import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
import uiautomator2 as u2
import xml.etree.ElementTree as ET
import time, re

d = u2.connect()

def find_edits_by_id():
    """Найти все EditText с resource-id android:id/input по координатам."""
    h = d.dump_hierarchy()
    root = ET.fromstring(h)
    out = []
    for node in root.iter('node'):
        cls = node.get('class','')
        rid = node.get('resource-id','')
        if cls == 'android.widget.EditText' and rid == 'android:id/input':
            b = node.get('bounds','')
            m = b.replace('[','').replace(']','-').split('-')
            x1,y1 = [int(x) for x in m[0].split(',')]
            x2,y2 = [int(x) for x in m[1].split(',')]
            out.append({'cx': (x1+x2)//2, 'cy': (y1+y2)//2, 'y1': y1})
    out.sort(key=lambda e: e['y1'])
    return out

def find_label_y(label):
    """Найти Y-координату текста-метки."""
    h = d.dump_hierarchy()
    root = ET.fromstring(h)
    for node in root.iter('node'):
        if node.get('text','') == label:
            b = node.get('bounds','')
            m = b.replace('[','').replace(']','-').split('-')
            return int(m[0].split(',')[1])
    return -1

# Сейчас мы на странице деталей сети с уже раскрытыми полями
# Скроллим чтобы видеть все 3 поля
print("scroll to see input fields...")
for _ in range(5):
    edits = find_edits_by_id()
    if len(edits) >= 2:
        print(f"found {len(edits)} edits at y={[e['y1'] for e in edits]}")
        break
    d.swipe(540, 1800, 540, 700, 0.4)
    time.sleep(0.4)

edits = find_edits_by_id()
print(f"editable inputs found: {len(edits)}")

# Заполняем host (первый) и port (второй)
if edits:
    # host
    e = edits[0]
    print(f">>> tap host @ ({e['cx']},{e['cy']})")
    d.click(e['cx'], e['cy'])
    time.sleep(0.6)
    d.send_keys(LAN_IP, clear=True)
    print(f"typed: {LAN_IP}")
    time.sleep(0.8)
    # скроллим вниз чтобы port был видим
    d.swipe(540, 1800, 540, 1000, 0.4)
    time.sleep(0.6)
    edits = find_edits_by_id()
    if len(edits) >= 2:
        # port (второй EditText в текущем скролле)
        e = edits[1]
        print(f">>> tap port @ ({e['cx']},{e['cy']})")
        d.click(e['cx'], e['cy'])
        time.sleep(0.6)
        d.send_keys("8080", clear=True)
        print("typed: 8080")
        time.sleep(0.8)

# Кнопка "Сохранить"
print(">>> finding Save button...")
d.swipe(540, 1800, 540, 700, 0.4)
time.sleep(0.5)
for txt in ["Сохранить","Save","ОК","OK"]:
    if d(text=txt).exists:
        d(text=txt).click()
        print(f"  saved via '{txt}'"); break

time.sleep(2)
d.screenshot("scout/v6_final.png")
# проверка результата
texts = re.findall(r'text="([^"]+)"', d.dump_hierarchy())
print("\nfinal screen texts with proxy info:")
for t in texts:
    if any(k in t for k in ["192.168", "8080", "Прокси", "Proxy"]):
        print(f"  {t}")
