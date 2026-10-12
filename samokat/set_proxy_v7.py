import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
import uiautomator2 as u2
import xml.etree.ElementTree as ET
import time, re

d = u2.connect()
ADB_SHELL = lambda cmd: d.shell(cmd).output

def find_edits():
    h = d.dump_hierarchy()
    root = ET.fromstring(h)
    out = []
    for node in root.iter('node'):
        if node.get('class') == 'android.widget.EditText':
            b = node.get('bounds','')
            m = b.replace('[','').replace(']','-').split('-')
            x1,y1 = [int(x) for x in m[0].split(',')]
            x2,y2 = [int(x) for x in m[1].split(',')]
            out.append({'cx': (x1+x2)//2, 'cy': (y1+y2)//2, 'y1': y1, 'text': node.get('text','')})
    out.sort(key=lambda e: e['y1'])
    return out

# Скроллим к полям
for _ in range(5):
    if len(find_edits()) >= 2: break
    d.swipe(540, 1800, 540, 700, 0.4); time.sleep(0.4)

edits = find_edits()
print(f"editable inputs: {len(edits)}")
for i, e in enumerate(edits):
    print(f"  {i}: y={e['y1']} cx={e['cx']} text={e['text']!r}")

# Заполняем через `adb shell input text` (работает без clipboard/IME)
if len(edits) >= 1:
    e = edits[0]
    print(f">>> tap host at ({e['cx']},{e['cy']})")
    d.click(e['cx'], e['cy'])
    time.sleep(0.5)
    # очистка через select-all + delete
    d.shell("input keyevent KEYCODE_MOVE_END")
    for _ in range(20):
        d.shell("input keyevent KEYCODE_DEL")
    time.sleep(0.3)
    d.shell(f"input text '{LAN_IP}'")
    print("  host typed via adb")
    time.sleep(0.6)

if len(edits) >= 2:
    e = edits[1]
    print(f">>> tap port at ({e['cx']},{e['cy']})")
    d.click(e['cx'], e['cy'])
    time.sleep(0.5)
    d.shell("input keyevent KEYCODE_MOVE_END")
    for _ in range(10):
        d.shell("input keyevent KEYCODE_DEL")
    time.sleep(0.3)
    d.shell("input text '8080'")
    print("  port typed via adb")
    time.sleep(0.6)

# скроллим к Save
print(">>> scrolling for Save button")
for _ in range(4):
    if any(d(text=t).exists for t in ["Сохранить","Save","ОК","OK"]): break
    d.swipe(540, 1800, 540, 700, 0.4); time.sleep(0.4)
for txt in ["Сохранить","Save","ОК","OK"]:
    if d(text=txt).exists:
        d(text=txt).click(); print(f"  saved via '{txt}'"); break

time.sleep(2)
d.screenshot("scout/v7_final.png")
# проверка
h = d.dump_hierarchy()
texts = re.findall(r'text="([^"]+)"', h)
print("\n--- final ---")
for t in texts:
    if "192.168" in t or "8080" in t or "Прокси-сервер" in t or "Подключено" in t:
        print(f"  '{t}'")
