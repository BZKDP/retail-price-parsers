"""
Прогоняет out/products.txt через HEAD/GET и оставляет только живые ссылки (HTTP 200).
Многопоточно. Промежуточно пишет прогресс — можно прервать и продолжить.

Результат:
  out/products_alive.txt   — только 200
  out/products_dead.txt    — 404 и прочие не-200 (с кодом в начале строки)
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).parent
IN_FILE = ROOT / "out" / "products.txt"
ALIVE = ROOT / "out" / "products_alive.txt"
DEAD = ROOT / "out" / "products_dead.txt"

WORKERS = 24
TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def load_done() -> set[str]:
    done: set[str] = set()
    for p in (ALIVE, DEAD):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                # alive: голая ссылка, dead: "404  <url>"
                url = line.split(maxsplit=1)[-1] if line[:3].isdigit() else line
                done.add(url.strip())
    return done


def check(url: str, session: requests.Session) -> tuple[str, int]:
    try:
        # HEAD у магнита может отдавать неконсистентные коды — берём GET stream
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT,
                        allow_redirects=True, stream=True)
        code = r.status_code
        r.close()
        return url, code
    except requests.RequestException:
        return url, 0  # сеть/таймаут


def main() -> int:
    urls = [u.strip() for u in IN_FILE.read_text(encoding="utf-8").splitlines() if u.strip()]
    done = load_done()
    todo = [u for u in urls if u not in done]
    print(f"Всего: {len(urls)}  уже проверено: {len(done)}  осталось: {len(todo)}")

    ALIVE.parent.mkdir(parents=True, exist_ok=True)
    f_alive = ALIVE.open("a", encoding="utf-8")
    f_dead = DEAD.open("a", encoding="utf-8")

    n_ok = n_bad = n_err = 0
    started = time.time()
    session = requests.Session()

    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(check, u, session): u for u in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                url, code = fut.result()
                if code == 200:
                    f_alive.write(url + "\n")
                    n_ok += 1
                elif code == 0:
                    f_dead.write(f"ERR  {url}\n")
                    n_err += 1
                else:
                    f_dead.write(f"{code}  {url}\n")
                    n_bad += 1
                if i % 200 == 0:
                    f_alive.flush(); f_dead.flush()
                    rate = i / (time.time() - started)
                    eta = (len(todo) - i) / rate if rate else 0
                    print(f"  {i:>6d}/{len(todo)}  ok={n_ok} bad={n_bad} err={n_err}  "
                          f"{rate:.1f}/s  ETA {eta:.0f}s")
    finally:
        f_alive.close()
        f_dead.close()

    print(f"\nГотово: ok={n_ok}  bad={n_bad}  err={n_err}")
    print(f"  -> {ALIVE}")
    print(f"  -> {DEAD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
