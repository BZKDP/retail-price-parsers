"""Тест прямого вызова API Самоката с RU-VPS, используя перехваченные headers."""
import json, os, requests

# headers.json — перехваченный набор заголовков (authorization, x-user-id, cookie...).
HEADERS_FILE = os.environ.get("SAMOKAT_HEADERS_FILE", "headers.json")
SHOWCASE = os.environ.get("SAMOKAT_SHOWCASE_ID", "")
H = json.load(open(HEADERS_FILE, encoding="utf-8"))

print("ip:", requests.get("https://ipinfo.io/json", timeout=10).json().get("ip"))

# CATEGORIES
r = requests.get(
    f"https://api.samokat.ru/showcase/v2/showcases/{SHOWCASE}/categories/list",
    headers=H, timeout=30,
)
print("\n== CATEGORIES ==")
print(f"  HTTP {r.status_code}  len={len(r.text)}")
print(f"  body[:500]:")
print(r.text[:500])

# SEARCH
r = requests.post(
    "https://api.samokat.ru/showcase/search/products",
    headers={**H, "Content-Type": "application/json"},
    json={"query": "молоко", "showcaseIds": [SHOWCASE]},
    timeout=30,
)
print("\n== SEARCH ==")
print(f"  HTTP {r.status_code}  len={len(r.text)}")
print(f"  body[:800]:")
print(r.text[:800])
