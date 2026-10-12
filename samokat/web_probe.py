"""Открыть samokat.ru через Chrome, пройти ServicePipe challenge,
собрать все api/XHR/fetch запросы которые делает страница.
Сохраняет cookies и список endpoints в out/."""
import json, time, pathlib, sys
from playwright.sync_api import sync_playwright

OUT = pathlib.Path("out"); OUT.mkdir(exist_ok=True)
PROFILE = str(pathlib.Path("chrome_profile").resolve())

requests_log = []

def on_request(req):
    if req.resource_type in ("xhr", "fetch") or "api" in req.url or "samokat" in req.url:
        requests_log.append({
            "method": req.method,
            "url": req.url,
            "headers": dict(req.headers),
            "resource_type": req.resource_type,
        })

def on_response(resp):
    try:
        if "samokat" in resp.url and resp.request.resource_type in ("xhr", "fetch"):
            body = None
            try:
                body = resp.text()[:2000]
            except Exception:
                pass
            requests_log.append({
                "_kind": "response",
                "status": resp.status,
                "url": resp.url,
                "body_preview": body,
            })
    except Exception as e:
        print("resp err", e)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE,
        headless=False,
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        locale="ru-RU",
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = ctx.new_page()
    page.on("request", on_request)
    page.on("response", on_response)

    print(">>> open samokat.ru")
    page.goto("https://samokat.ru/", wait_until="domcontentloaded", timeout=60000)
    print("   title after dom:", page.title())

    # Ждём прохождение challenge — обычно <10 секунд
    for i in range(15):
        time.sleep(1)
        try:
            cookies = ctx.cookies()
            names = {c["name"] for c in cookies}
            print(f"   t+{i}s  cookies: {sorted(names)}  url={page.url}")
            if "spid" in names or "spsn" in names:
                # ещё пара секунд чтобы page догрузилась
                time.sleep(3)
                break
        except Exception as e:
            print("err", e)

    print("\n>>> final page state")
    print("   url:", page.url)
    print("   title:", page.title())
    page.screenshot(path=str(OUT / "samokat_web_landing.png"), full_page=True)

    # Cookies
    cookies = ctx.cookies()
    (OUT / "cookies.json").write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   saved {len(cookies)} cookies → out/cookies.json")

    # Заодно попробуем доскроллить главную и пощёлкать «Каталог»
    print("\n>>> try clicking around")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception as e:
        print("   networkidle timeout:", e)

    # Сохраняем HTML
    (OUT / "samokat_web_landing.html").write_text(page.content(), encoding="utf-8")
    print("   saved HTML → out/samokat_web_landing.html")

    (OUT / "requests.json").write_text(json.dumps(requests_log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   saved {len(requests_log)} request entries → out/requests.json")

    time.sleep(2)
    ctx.close()
print("DONE")
