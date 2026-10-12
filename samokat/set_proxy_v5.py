import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
import uiautomator2 as u2
import time, re

d = u2.connect()

def texts():
    return re.findall(r'text="([^"]+)"', d.dump_hierarchy())

def click_dialog_ok():
    """Найти и кликнуть ОК в диалоге"""
    for t in ["ОК", "OK", "Сохранить", "Save", "Готово", "Done", "Применить"]:
        if d(text=t).exists:
            d(text=t).click(); return t
    return None

# Сейчас на странице "Подробности MTS_HOME-5_9D70" с раскрытыми полями прокси
# Прокручиваем чтобы видеть "Имя хоста"

print(">>> step 1: scroll to host field")
for _ in range(5):
    if d(text="Имя хоста").exists or d(text="Host").exists:
        break
    d.swipe(540, 1800, 540, 700, 0.4)
    time.sleep(0.4)

print(">>> step 2: click 'Имя хоста'")
host_label = d(text="Имя хоста")
if host_label.exists:
    host_label.click()
    time.sleep(1.2)
    d.screenshot("scout/v5_host_dialog.png")
    print("  texts:", [t for t in texts() if t.strip()][:15])
    # Должен открыться диалог с EditText
    edits = d.xpath('//*[@class="android.widget.EditText"]').all()
    print(f"  EditText: {len(edits)}")
    if edits:
        edits[0].click(); time.sleep(0.3)
        d.clear_text(); d.send_keys(LAN_IP, clear=False)
        print(f"  typed {LAN_IP}")
        time.sleep(0.5)
        ok = click_dialog_ok()
        print(f"  dialog OK: {ok}")
        time.sleep(1)
else:
    # fallback: тапнуть на текст "proxy.example.com"
    if d(textContains="proxy.example").exists:
        d(textContains="proxy.example").click()
        time.sleep(1)
        d.screenshot("scout/v5_host_fallback.png")
        edits = d.xpath('//*[@class="android.widget.EditText"]').all()
        if edits:
            edits[0].click(); time.sleep(0.3)
            d.clear_text(); d.send_keys(LAN_IP, clear=False)
            click_dialog_ok()

time.sleep(1)
# Скроллим вниз чтобы открылся порт
print(">>> step 3: scroll to port field")
for _ in range(5):
    if d(text="Порт").exists or d(text="Port").exists or d(text="Порт прокси").exists:
        break
    d.swipe(540, 1800, 540, 700, 0.4)
    time.sleep(0.4)

print(">>> step 4: click 'Порт'")
port_label = d(text="Порт") or d(text="Port") or d(text="Порт прокси")
if port_label.exists:
    port_label.click()
    time.sleep(1.2)
    d.screenshot("scout/v5_port_dialog.png")
    edits = d.xpath('//*[@class="android.widget.EditText"]').all()
    if edits:
        edits[0].click(); time.sleep(0.3)
        d.clear_text(); d.send_keys("8080", clear=False)
        print("  typed 8080")
        time.sleep(0.5)
        click_dialog_ok()
        time.sleep(1)
d.screenshot("scout/v5_final.png")
print(">>> done")
print("final texts:", [t for t in texts() if t.strip() and ("прокси" in t.lower() or "192.168" in t or "8080" in t)])
