import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
import uiautomator2 as u2
import time, re

d = u2.connect()

def all_texts():
    h = d.dump_hierarchy()
    return [m for m in re.findall(r'text="([^"]+)"', h)]

def click_text(*variants, scroll_first=True):
    """Click first text variant found, scrolling if needed."""
    for _ in range(6):
        for v in variants:
            if d(text=v).exists:
                d(text=v).click()
                return v
        if not scroll_first: return None
        d.swipe(540, 1800, 540, 700, 0.4)
        time.sleep(0.4)
    return None

print(">>> step 1: open Wi-Fi details directly (re-open if needed)")
d.shell("am start -a android.settings.WIFI_SETTINGS")
time.sleep(2)
# на главной Wi-Fi видим список сетей; кликнем по MTS_HOME-5_9D70
if d(textContains="MTS_HOME").exists:
    d(textContains="MTS_HOME").click()
    time.sleep(1.5)

print(">>> step 2: open proxy dialog")
v = click_text("Прокси-сервер", "Веб-прокси", "Proxy")
print(f"  clicked: {v}")
time.sleep(1.5)

print(">>> step 3: select Manual")
v = click_text("Настройка вручную", "Manual", "Вручную", scroll_first=False)
print(f"  clicked: {v}")
time.sleep(2)
d.screenshot("scout/v4_manual.png")
print("texts after manual:", [t for t in all_texts() if t.strip()][:20])

print(">>> step 4: fill host")
# Тапнем по плейсхолдеру 'proxy.example.com' или по полю под надписью 'Имя хоста'
filled_host = False
edits = d.xpath('//*[@class="android.widget.EditText"]').all()
print(f"EditText count: {len(edits)}")
for i, e in enumerate(edits):
    info = e.info
    print(f"  edit{i}: text={info.get('text')!r} bounds={info.get('bounds')}")
if edits:
    edits[0].click(); time.sleep(0.3)
    d.clear_text(); d.send_keys(LAN_IP, clear=False)
    filled_host = True
    print("  host filled")
time.sleep(1)
d.screenshot("scout/v4_host.png")

# Скроллим вниз — клавиатура накрыла поля порта
d.swipe(540, 1500, 540, 700, 0.4)
time.sleep(0.5)
edits = d.xpath('//*[@class="android.widget.EditText"]').all()
print(f"after scroll EditText count: {len(edits)}")
for i, e in enumerate(edits):
    info = e.info
    print(f"  edit{i}: text={info.get('text')!r}")

# второй EditText (с placeholder 8080) — это порт
filled_port = False
if len(edits) >= 2:
    edits[1].click(); time.sleep(0.3)
    d.clear_text(); d.send_keys("8080", clear=False)
    filled_port = True
    print("  port filled")
time.sleep(1)
d.screenshot("scout/v4_port.png")

# скроллим ещё и ищем Save
d.swipe(540, 1500, 540, 700, 0.4)
time.sleep(0.5)
v = click_text("Сохранить", "Save", "ОК", "OK", scroll_first=False)
print(f"  save clicked: {v}")
time.sleep(2)
d.screenshot("scout/v4_saved.png")
print("done")
