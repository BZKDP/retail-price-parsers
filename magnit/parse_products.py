"""
Парсер карточек товаров magnit.ru.
Источник данных: <script type="application/ld+json"> на странице товара —
schema.org Product + BreadcrumbList. Никакого браузера, чистый requests.

Вход:
  out/products.txt          (или products_alive.txt, если уже отфильтровано)

Выход (append, по одной строке на товар):
  out/products.jsonl        — полная запись по товару
  out/products.csv          — основные поля
  out/parse.log             — лог: успехи, 404, ретраи, ошибки парсинга

Особенности:
  - многопоточный (WORKERS)
  - ретраи на 429/5xx с экспоненциальной паузой
  - возобновляемый: пропускает url, которые уже есть в products.jsonl
  - корректная обработка отсутствующих JSON-LD (битые/пустые страницы)
  - регион магазина по умолчанию = тот, что отдаёт WAF по нашему IP
    (Краснодар). Если нужен другой — задать SHOP_CODE/COOKIES ниже.
"""

import csv
import json
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from curl_cffi import requests  # имитация TLS Chrome — обход Qrator
from curl_cffi.requests.exceptions import RequestException as CurlRequestError
from bs4 import BeautifulSoup

# ---------- Настройки ----------
ROOT = Path(__file__).parent
OUT = ROOT / "out"
IN_FILE_PREFERRED = OUT / "products_alive.txt"   # если был фильтр
IN_FILE_FALLBACK = OUT / "products.txt"
JSONL = OUT / "products.jsonl"
CSV_FILE = OUT / "products.csv"
LOG_FILE = OUT / "parse.log"

WORKERS = 8
TIMEOUT = 25
MAX_RETRIES = 4
THROTTLE_ON_429 = 5.0
THROTTLE_ON_423 = 20.0
PER_REQUEST_DELAY = 0.15
IMPERSONATE = "chrome124"   # TLS+H2 fingerprint браузера

# Куки региона/магазина. Магнит сам подставляет дефолт.
# Чтобы парсить конкретный магазин — заполни shopCode и x_shop_type значениями
# из cookies своего браузера после выбора магазина на magnit.ru
# (DevTools -> Application -> Cookies -> magnit.ru). Форматы типов: MM_MINI, ME и т.д.
# shopCode передаётся только в URL — если положить в cookie, магнит отвечает 404.
COOKIES: dict[str, str] = {
    "x_shop_type": os.environ.get("MAGNIT_SHOP_TYPE", "MM_MINI"),
}
URL_PARAMS: dict[str, str] = {
    "shopCode": os.environ.get("MAGNIT_SHOP_CODE", "000000"),
}

# ---------- Логирование ----------
OUT.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("magnit")

# ---------- HTTP ----------
SESSION_LOCAL = threading.local()


def session() -> requests.Session:
    s = getattr(SESSION_LOCAL, "s", None)
    if s is None:
        s = requests.Session(impersonate=IMPERSONATE)
        s.headers.update({
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Referer": "https://magnit.ru/",
        })
        if COOKIES:
            for k, v in COOKIES.items():
                s.cookies.set(k, v, domain=".magnit.ru")
        # прогрев — открыть главную, получить куки сессии
        try:
            r = s.get("https://magnit.ru/", timeout=TIMEOUT)
            log.debug("warmup %d cookies=%d", r.status_code, len(s.cookies))
        except CurlRequestError as e:
            log.warning("warmup failed: %s", e)
        SESSION_LOCAL.s = s
    return s


def _pace() -> None:
    """Минимальная пауза между запросами в рамках одного потока."""
    last = getattr(SESSION_LOCAL, "last_ts", 0.0)
    dt = time.time() - last
    if dt < PER_REQUEST_DELAY:
        time.sleep(PER_REQUEST_DELAY - dt)
    SESSION_LOCAL.last_ts = time.time()


def fetch_html(url: str) -> tuple[int, str | None]:
    """Возвращает (http_code, html|None)."""
    for attempt in range(1, MAX_RETRIES + 1):
        _pace()
        try:
            r = session().get(url, timeout=TIMEOUT, allow_redirects=True,
                              params=URL_PARAMS or None)
            if r.status_code == 200:
                return 200, r.text
            if r.status_code in (404, 410):
                return r.status_code, None
            if r.status_code == 429:
                log.warning("429 throttled %s (attempt %d)", url, attempt)
                time.sleep(THROTTLE_ON_429 * attempt)
                continue
            if r.status_code == 423:
                log.warning("423 Locked (WAF) %s — пауза %.0fs (attempt %d)",
                            url, THROTTLE_ON_423 * attempt, attempt)
                time.sleep(THROTTLE_ON_423 * attempt)
                # пересоздаём сессию — куки могли протухнуть
                SESSION_LOCAL.s = None
                continue
            if 500 <= r.status_code < 600:
                log.warning("HTTP %d %s (attempt %d)", r.status_code, url, attempt)
                time.sleep(1.5 * attempt)
                continue
            return r.status_code, None
        except CurlRequestError as e:
            log.warning("net err %s on %s (attempt %d)", e, url, attempt)
            time.sleep(1.5 * attempt)
    return 0, None


# ---------- Парсинг ----------
LDJSON_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S,
)


def find_jsonld(html: str) -> list[Any]:
    out = []
    for raw in LDJSON_RE.findall(html):
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def parse_details_section(soup: BeautifulSoup) -> dict[str, Any]:
    """
    Парсит блоки 'Описание / Характеристики / Условия хранения /
    Дополнительная информация' из section.product-details-parameters.
    Возвращает словарь:
      {
        "description":           str | None,
        "characteristics":       [{name, value}, ...],
        "storage_conditions":    [{name, value}, ...],
        "additional_info":       str | None,
      }
    """
    out: dict[str, Any] = {
        "description": None,
        "characteristics": [],
        "storage_conditions": [],
        "additional_info": None,
    }
    section = soup.select_one("section.product-details-parameters")
    if not section:
        return out

    LABEL_MAP = {
        "Описание": "description",
        "Характеристики": "characteristics",
        "Условия хранения": "storage_conditions",
        "Дополнительная информация": "additional_info",
    }

    for item in section.select(".product-details-parameters__item"):
        title_el = item.select_one(".product-details-parameters__item-title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        key = LABEL_MAP.get(title)
        if not key:
            continue
        content = item.select_one(".product-details-parameters__item-content")
        if not content:
            continue
        # текстовые блоки
        flat = content.select_one(".product-details-parameters-flat")
        if flat:
            out[key] = flat.get_text(" ", strip=True) or None
            continue
        # list-блоки (Характеристики, Условия хранения)
        rows = []
        for it in content.select(".product-details-parameters-list__item"):
            spans = it.find_all("span", class_="pl-text")
            if len(spans) >= 2:
                rows.append({
                    "name": spans[0].get_text(strip=True),
                    "value": spans[-1].get_text(strip=True),
                })
        out[key] = rows
    return out


def parse_current_shop(soup: BeautifulSoup, html: str) -> dict[str, Any]:
    """Достаём данные о текущем магазине из title и meta-тегов."""
    title_el = soup.select_one("title")
    title = title_el.get_text(strip=True) if title_el else None
    shop_addr = None
    if title and "|" in title:
        # формат: "Название – купить ... из магазина Магнит | <адрес>"
        shop_addr = title.split("|", 1)[-1].strip() or None
    return {"shop_address": shop_addr}


def extract(url: str, html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    blocks = find_jsonld(html)
    product = next(
        (b for b in blocks
         if isinstance(b, dict) and b.get("@type") == "Product"),
        None,
    )
    if not product:
        return None
    crumbs = next(
        (b for b in blocks
         if isinstance(b, dict) and b.get("@type") == "BreadcrumbList"),
        None,
    )
    categories: list[str] = []
    if crumbs:
        for it in crumbs.get("itemListElement", []):
            name = it.get("name")
            if name:
                categories.append(name)

    offers = product.get("offers") or {}
    rating = product.get("aggregateRating") or {}
    details = parse_details_section(soup)
    shop = parse_current_shop(soup, html)

    return {
        "url": url,
        "sku": product.get("sku"),
        "name": product.get("name"),
        "brand": product.get("brand"),
        "manufacturer": product.get("manufacturer"),
        "weight": product.get("weight"),
        "price": offers.get("price") if isinstance(offers, dict) else None,
        "currency": offers.get("priceCurrency") if isinstance(offers, dict) else None,
        "image": (product.get("image") or [None])[0]
                 if isinstance(product.get("image"), list)
                 else product.get("image"),
        "description": details["description"] or product.get("description"),
        "characteristics": details["characteristics"],
        "storage_conditions": details["storage_conditions"],
        "additional_info": details["additional_info"],
        "rating_value": rating.get("ratingValue"),
        "rating_count": rating.get("ratingCount"),
        "review_count": rating.get("reviewCount"),
        "categories": categories,
        "shop_address": shop["shop_address"],
        "reviews": product.get("review"),
    }


# ---------- Хранилище ----------
_write_lock = threading.Lock()


def load_done_urls() -> set[str]:
    if not JSONL.exists():
        return set()
    done: set[str] = set()
    with JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["url"])
            except Exception:
                pass
    return done


CSV_COLS = ["sku", "name", "brand", "manufacturer", "weight",
            "price", "currency",
            "rating_value", "rating_count", "review_count",
            "categories", "description",
            "characteristics", "storage_conditions", "additional_info",
            "shop_address", "image", "url"]


def append_record(rec: dict) -> None:
    with _write_lock:
        with JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        new_csv = not CSV_FILE.exists()
        with CSV_FILE.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new_csv:
                w.writerow(CSV_COLS)
            row = []
            for c in CSV_COLS:
                v = rec.get(c)
                if isinstance(v, list):
                    v = " / ".join(map(str, v))
                row.append(v)
            w.writerow(row)


# ---------- Воркер ----------
COUNTERS = {"ok": 0, "404": 0, "nojsonld": 0, "neterr": 0, "other": 0}
COUNTERS_LOCK = threading.Lock()


def worker(url: str) -> None:
    code, html = fetch_html(url)
    if code == 200 and html:
        rec = extract(url, html)
        if rec is None:
            with COUNTERS_LOCK:
                COUNTERS["nojsonld"] += 1
            log.warning("no JSON-LD Product on %s", url)
            return
        append_record(rec)
        with COUNTERS_LOCK:
            COUNTERS["ok"] += 1
        return
    if code in (404, 410):
        with COUNTERS_LOCK:
            COUNTERS["404"] += 1
        log.info("dead %d %s", code, url)
        return
    if code == 0:
        with COUNTERS_LOCK:
            COUNTERS["neterr"] += 1
        return
    with COUNTERS_LOCK:
        COUNTERS["other"] += 1
    log.warning("HTTP %d (final) %s", code, url)


# ---------- Main ----------
def main() -> int:
    in_file = IN_FILE_PREFERRED if IN_FILE_PREFERRED.exists() else IN_FILE_FALLBACK
    if not in_file.exists():
        log.error("Не найден список ссылок: %s", in_file)
        return 1

    urls = [u.strip() for u in in_file.read_text(encoding="utf-8").splitlines() if u.strip()]
    done = load_done_urls()
    todo = [u for u in urls if u not in done]
    log.info("Источник: %s", in_file.name)
    log.info("Всего: %d  уже распаршено: %d  осталось: %d",
             len(urls), len(done), len(todo))

    started = time.time()
    last_report = started

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(worker, u) for u in todo]
        for i, _ in enumerate(as_completed(futs), 1):
            now = time.time()
            if now - last_report > 5 or i == len(todo):
                rate = i / (now - started) if now > started else 0
                eta = (len(todo) - i) / rate if rate else 0
                with COUNTERS_LOCK:
                    snap = dict(COUNTERS)
                log.info(
                    "progress %d/%d  %.1f/s  ETA %.0fs  ok=%d 404=%d "
                    "nojsonld=%d neterr=%d other=%d",
                    i, len(todo), rate, eta,
                    snap["ok"], snap["404"], snap["nojsonld"],
                    snap["neterr"], snap["other"],
                )
                last_report = now

    log.info("FINISH counters=%s", COUNTERS)
    log.info("  JSONL: %s", JSONL)
    log.info("  CSV:   %s", CSV_FILE)
    log.info("  LOG:   %s", LOG_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
