"""
Разовый сбор всех ссылок ассортимента magnit.ru из sitemap.
Источник: https://magnit.ru/sitemap_index.xml
  -> __sitemap__/catalog.xml   (категории, ~746 шт.)
  -> __sitemap__/products.xml  (товары)
  -> __sitemap__/promo-catalog.xml, pages.xml, content-pages.xml (доп.)

Результат:
  out/products.txt   — все ссылки на карточки товаров
  out/catalog.txt    — все ссылки на категории
  out/all_links.txt  — объединённый список (уникальный)
  out/sitemaps_raw/  — сырые xml на всякий случай
"""

import gzip
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import requests

SITEMAP_INDEX = "https://magnit.ru/sitemap_index.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

OUT = Path(__file__).parent / "out"
RAW = OUT / "sitemaps_raw"


def fetch(url: str, retries: int = 4, timeout: int = 30) -> bytes:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            data = r.content
            # На случай gzip без правильного Content-Encoding
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            return data
        except Exception as e:
            last_exc = e
            print(f"  [retry {attempt}/{retries}] {url}: {e}", file=sys.stderr)
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"Не удалось скачать {url}: {last_exc}")


def save_raw(url: str, data: bytes) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    name = Path(urlparse(url).path).name or "root.xml"
    (RAW / name).write_bytes(data)


def parse_urls(xml_bytes: bytes) -> tuple[list[str], list[str]]:
    """Возвращает (вложенные_sitemap, обычные_url)."""
    root = ET.fromstring(xml_bytes)
    tag = root.tag.split("}", 1)[-1]
    sub_sitemaps: list[str] = []
    page_urls: list[str] = []
    if tag == "sitemapindex":
        for sm in root.findall("sm:sitemap/sm:loc", NS):
            if sm.text:
                sub_sitemaps.append(sm.text.strip())
    elif tag == "urlset":
        for loc in root.findall("sm:url/sm:loc", NS):
            if loc.text:
                page_urls.append(loc.text.strip())
    else:
        print(f"  ! неизвестный корневой тег: {tag}", file=sys.stderr)
    return sub_sitemaps, page_urls


def crawl(start_url: str) -> dict[str, list[str]]:
    """
    Возвращает {имя_sitemap_файла: [url, ...]}.
    Ключ — имя файла последнего sitemap (catalog, products, ...).
    """
    by_source: dict[str, list[str]] = {}
    queue = [start_url]
    seen: set[str] = set()
    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        print(f"-> {url}")
        data = fetch(url)
        save_raw(url, data)
        subs, urls = parse_urls(data)
        if subs:
            queue.extend(subs)
        if urls:
            key = Path(urlparse(url).path).stem  # 'products', 'catalog', ...
            by_source.setdefault(key, []).extend(urls)
        time.sleep(0.3)
    return by_source


def write_list(path: Path, items: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(items) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    by_source = crawl(SITEMAP_INDEX)

    print("\n=== Итог по источникам ===")
    for key, urls in by_source.items():
        uniq = sorted(set(urls))
        write_list(OUT / f"{key}.txt", uniq)
        print(f"  {key:>15s}: {len(uniq):>7d}  -> out/{key}.txt")

    all_links = sorted({u for urls in by_source.values() for u in urls})
    write_list(OUT / "all_links.txt", all_links)
    print(f"  {'ВСЕГО уникальных':>15s}: {len(all_links):>7d}  -> out/all_links.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
