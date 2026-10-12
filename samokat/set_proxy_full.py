import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
import uiautomator2 as u2
import time
import re

d = u2.connect()

def dump_texts():
    h = d.dump_hierarchy()
    return [m for m in re.findall(r'text="([^"]+)"', h) if m.strip()]

def dump_edits():
    h = d.dump_hierarchy()
    # ищем EditText с их координатами и текстом
    out = []
    for m in re.finditer(r'<node[^>]*class="android\.widget\.EditText"([^/]*?)bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', h):
        attrs = m.group(1)
        text_m = re.search(r'text="([^"]*)"', attrs)
        hint_m = re.search(r'hint="([^"]*)"', attrs)
        out.append({
            "text": text_m.group(1) if text_m else "",
            "hint": hint_m.group(1) if hint_m else "",
            "x1": int(m.group(2)), "y1": int(m.group(3)),
            "x2": int(m.group(4)), "y2": int(m.group(5)),
        })
    return out

print("1) open WIFI settings...")
d.shell("am start -a android.settings.WIFI_SETTINGS")
time.sleep(2)

print("2) click connected network...")
d(text="Подключено").click()
time.sleep(1.5)

print("3) scroll until Web-proxy + click...")
for i in range(6):
    if d(text="Веб-прокси").exists:
        d(text="Веб-прокси").click()
        break
    d.swipe(540, 1800, 540, 600, 0.4)
    time.sleep(0.4)
time.sleep(1.5)

print("4) click 'Настройка вручную'...")
d(text="Настройка вручную").click()
time.sleep(1.5)

print("5) fill host + port + save (no back-press between)")
for attempt in range(8):
    edits = dump_edits()
    texts = dump_texts()
    print(f"  attempt {attempt}: edits={len(edits)}  visible: {[t for t in texts if t in ('Имя хоста','Порт','Порт прокси','Сохранить','Save','Отмена','Cancel','Bypass','Обход','прокси')][:8]}")
    # ищем редактируемые поля по подсказкам
    host_edit = next((e for e in edits if "proxy.example" in (e.get("hint","")+e.get("text","")).lower() or "хоста" in (e.get("hint","")+e.get("text","")).lower()), None)
    port_edit = next((e for e in edits if "8080" in (e.get("hint","")+e.get("text","")) or "порт" in (e.get("hint","")+e.get("text","")).lower() or e is not host_edit), None)
    if host_edit and (not host_edit.get("text") or host_edit["text"]=="proxy.example.com"):
        cx = (host_edit["x1"]+host_edit["x2"])//2
        cy = (host_edit["y1"]+host_edit["y2"])//2
        d.click(cx, cy); time.sleep(0.4)
        d.clear_text(); time.sleep(0.2)
        d.send_keys(LAN_IP, clear=False)
        print(f"    host filled @ {cx},{cy}")
        time.sleep(0.6)
    if port_edit and port_edit is not host_edit and (not port_edit.get("text") or port_edit["text"]=="8080" or "порт" in port_edit.get("hint","").lower()):
        cx = (port_edit["x1"]+port_edit["x2"])//2
        cy = (port_edit["y1"]+port_edit["y2"])//2
        d.click(cx, cy); time.sleep(0.4)
        d.clear_text(); time.sleep(0.2)
        d.send_keys("8080", clear=False)
        print(f"    port filled @ {cx},{cy}")
        time.sleep(0.6)
    # после ввода скроллим и пробуем найти кнопку Save
    save_btn = None
    for txt in ["Сохранить","Save","ОК","OK"]:
        if d(text=txt).exists:
            save_btn = d(text=txt); break
    if save_btn:
        save_btn.click(); print(f"    save clicked"); break
    # скроллим
    d.swipe(540, 1800, 540, 900, 0.4)
    time.sleep(0.5)
time.sleep(2)
d.screenshot("scout/proxy_done.png")
print("\nproxy setup attempt finished")
