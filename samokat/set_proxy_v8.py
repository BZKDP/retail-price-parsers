import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
"""
Финальная версия: тапаем по координатам из dump'а, чистим через DEL,
печатаем через adb shell input text.
"""
import uiautomator2 as u2
import xml.etree.ElementTree as ET
import time, re

d = u2.connect()

def find_input_y(label_text):
    """Возвращает y-координату EditText, идущего сразу за TextView label_text."""
    h = d.dump_hierarchy()
    root = ET.fromstring(h)
    label_y = None
    candidates = []
    for node in root.iter('node'):
        cls = node.get('class','')
        text = node.get('text','')
        b = node.get('bounds','')
        m = b.replace('[','').replace(']','-').split('-')
        try:
            x1,y1 = [int(x) for x in m[0].split(',')]
            x2,y2 = [int(x) for x in m[1].split(',')]
        except: continue
        if text == label_text and cls == 'android.widget.TextView':
            label_y = y1
        if cls == 'android.widget.EditText':
            candidates.append({'cx':(x1+x2)//2,'cy':(y1+y2)//2,'y1':y1})
    if label_y is None or not candidates: return None
    # EditText сразу после label (y > label_y, ближайший)
    candidates.sort(key=lambda c: c['y1'])
    for c in candidates:
        if c['y1'] > label_y:
            return c
    return None

def scroll_until_visible(text):
    for _ in range(6):
        if d(text=text).exists: return True
        d.swipe(540, 1800, 540, 700, 0.4); time.sleep(0.4)
    return False

def fill_field(field_label, value, length_to_clear=30):
    print(f">>> filling '{field_label}' with {value!r}")
    scroll_until_visible(field_label)
    f = find_input_y(field_label)
    if not f:
        print(f"  ! no EditText for label {field_label}")
        return False
    d.click(f['cx'], f['cy'])
    time.sleep(0.5)
    # очистка
    d.shell("input keyevent KEYCODE_MOVE_END")
    for _ in range(length_to_clear):
        d.shell("input keyevent KEYCODE_DEL")
    time.sleep(0.3)
    # ввод
    d.shell(f"input text '{value}'")
    time.sleep(0.5)
    return True

fill_field("Имя хоста", LAN_IP)
# скроллим к Порт
d.shell("input keyevent KEYCODE_BACK")  # скрыть клавиатуру
time.sleep(0.6)
fill_field("Порт", "8080")
d.shell("input keyevent KEYCODE_BACK")  # скрыть клавиатуру
time.sleep(0.6)

# скриншот перед сохранением
d.screenshot("scout/v8_before_save.png")

# скроллим вниз чтобы найти Сохранить (в ColorOS она вверху)
print(">>> looking for Save button")
# в ColorOS обычно "Сохранить" вверху в нav-bar или внизу. Сначала вверх
for _ in range(3):
    d.swipe(540, 700, 540, 1800, 0.4); time.sleep(0.4)
saved = False
for txt in ["Сохранить","Save","ОК","OK","Готово","Done","Применить","Apply"]:
    if d(text=txt).exists:
        d(text=txt).click()
        print(f"  saved via '{txt}'"); saved = True; break
if not saved:
    # вниз
    for _ in range(3):
        d.swipe(540, 1800, 540, 700, 0.4); time.sleep(0.4)
        for txt in ["Сохранить","Save","ОК","OK","Готово","Done"]:
            if d(text=txt).exists:
                d(text=txt).click()
                print(f"  saved via '{txt}'"); saved = True; break
        if saved: break

time.sleep(3)
d.screenshot("scout/v8_final.png")

# Финальная проверка — должно появиться "<LAN_IP>:8080" или подобное на странице деталей сети
h = d.dump_hierarchy()
texts = re.findall(r'text="([^"]+)"', h)
print("\n--- final state ---")
hit = False
for t in texts:
    if LAN_IP in t or "8080" in t:
        print(f"  ✓ '{t}'"); hit = True
if not hit:
    print("  ⚠️ no LAN_IP/8080 visible")
    for t in texts[:30]:
        if t.strip(): print(f"    {t}")
