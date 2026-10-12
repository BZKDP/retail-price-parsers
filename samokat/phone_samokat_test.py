"""Тест запросов к Самокату с мобильного residential IP."""
import os, urllib.request, urllib.error, json

# Токен и идентификаторы берутся из окружения (перехватываются из трафика приложения).
JWT = os.environ.get("SAMOKAT_JWT", "")
USER_ID = os.environ.get("SAMOKAT_USER_ID", "")
SHOWCASE = os.environ.get("SAMOKAT_SHOWCASE_ID", "")

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "authorization": f"Bearer {JWT}",
    "systemversion": "12",
    "x-user-id": USER_ID,
    "x-user-type": "user",
    "x-application-platform": "android",
    "x-application-version": "3.233.0",
    "user-agent": "okhttp/4.12.0",
}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"  HTTP {r.status}  len={len(body)}")
            print(f"  body[:600]: {body[:600]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"  HTTP {e.code} {e.reason}  len={len(body)}")
        print(f"  body[:600]: {body[:600]}")
    except Exception as e:
        print(f"  ERR: {e!r}")

print("== IP check ==")
get("https://ipinfo.io/json")
print("\n== CATEGORIES ==")
get(f"https://api.samokat.ru/showcase/v2/showcases/{SHOWCASE}/categories/list")
