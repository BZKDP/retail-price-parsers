"""Пройти ServicePipe JS-challenge на web.samokat.ru,
получить cookies для домена .samokat.ru и попробовать дёрнуть api.samokat.ru."""
import json, time, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path("out"); OUT.mkdir(exist_ok=True)
PROFILE = str(pathlib.Path("profile_chromium").resolve())

requests_log = []

def on_request(req):
    requests_log.append({"phase": "req", "method": req.method, "url": req.url, "rtype": req.resource_type})

def on_response(resp):
    requests_log.append({"phase": "resp", "url": resp.url, "status": resp.status})

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE,
        headless=False,
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        locale="ru-RU",
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    page = ctx.new_page()
    page.on("request", on_request)
    page.on("response", on_response)

    print(">>> open web.samokat.ru")
    page.goto("https://web.samokat.ru/", wait_until="domcontentloaded", timeout=60000)

    # Долго ждём — ServicePipe должен выполниться, отредиректить, и загрузить app
    for i in range(45):
        time.sleep(1)
        cookies = ctx.cookies()
        names = sorted({c["name"] for c in cookies})
        title = page.title()
        url = page.url
        if i % 3 == 0:
            print(f"   t+{i:02d}s  url={url}  title={title!r}  cookies={names}")
        # успешно прошёл если title не пустой ИЛИ есть application контент
        try:
            txt = page.evaluate("document.body.innerText[:200]")
        except Exception:
            txt = ""
        if title and txt and "captcha" not in txt.lower() and len(txt) > 50:
            print("    !! page seems loaded, txt[:200]:", repr(txt))
            break

    page.screenshot(path=str(OUT / "web_final.png"), full_page=True)
    (OUT / "web_final.html").write_text(page.content(), encoding="utf-8")

    cookies = ctx.cookies()
    (OUT / "web_cookies.json").write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n>>> got {len(cookies)} cookies")
    for c in cookies:
        print(f"   {c['name']:30}  domain={c['domain']:20}  value[:60]={c['value'][:60]}")

    # Пробуем дёрнуть api.samokat.ru с этими cookies из того же браузера
    print("\n>>> trying api.samokat.ru/showcase from same context...")
    api = ctx.new_page()
    api.on("request", on_request)
    api.on("response", on_response)
    try:
        r = api.request.get(
            "https://api.samokat.ru/showcase/v2/showcases/e112432f-f3eb-4225-b273-cd1061cd2002/categories/list",
            headers={
                "accept": "application/json, text/plain, */*",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
                "origin": "https://web.samokat.ru",
                "referer": "https://web.samokat.ru/",
            },
        )
        body = r.text()[:1000]
        print(f"   status={r.status}  body_len={len(r.text())}  body[:500]={body[:500]!r}")
    except Exception as e:
        print("   api err:", e)

    (OUT / "requests2.json").write_text(json.dumps(requests_log, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(2)
    ctx.close()
print("DONE")
