import uiautomator2 as u2
import time, sys

d = u2.connect()
# мы УЖЕ в Details страница Wi-Fi после прошлого запуска
# Скроллим вниз чтобы найти "Прокси" / "Дополнительные настройки"
PROXY_LABELS = ["Прокси", "Proxy", "Веб-прокси", "Web Proxy", "Web-прокси", "Прокси-сервер"]
for i in range(5):
    d.screenshot(f"scout/scroll_{i}.png")
    proxy_elem = None
    for lbl in PROXY_LABELS:
        if d(text=lbl).exists:
            proxy_elem = d(text=lbl); print(f"FOUND proxy label: '{lbl}'"); break
    if proxy_elem:
        proxy_elem.click()
        time.sleep(1.5)
        d.screenshot("scout/after_proxy_click.png")
        break
    d.swipe(540, 1800, 540, 600, 0.4)
    time.sleep(0.6)

# дамп иерархии
hier = d.dump_hierarchy()
import re
# найдём текст-элементы для понимания структуры
texts = re.findall(r'text="([^"]+)"', hier)
print("\nVisible texts on current screen:")
for t in texts[:40]:
    if t.strip(): print(f"  '{t}'")
