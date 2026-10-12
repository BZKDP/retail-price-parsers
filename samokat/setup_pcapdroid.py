"""
1. Открыть Wi-Fi настройки → убрать прокси
2. Открыть PCAPdroid → настроить TLS decryption + фильтр Samokat → запустить
"""
import uiautomator2 as u2
import time, re
import xml.etree.ElementTree as ET

d = u2.connect()

def texts():
    return re.findall(r'text="([^"]+)"', d.dump_hierarchy())

def find_edit_after_label(label):
    h = d.dump_hierarchy()
    root = ET.fromstring(h)
    label_y = None
    edits = []
    for n in root.iter('node'):
        b = n.get('bounds','').replace('[','').replace(']','-').split('-')
        try:
            x1,y1 = [int(x) for x in b[0].split(',')]
            x2,y2 = [int(x) for x in b[1].split(',')]
        except: continue
        if n.get('text','') == label:
            label_y = y1
        if n.get('class') == 'android.widget.EditText':
            edits.append({'cx':(x1+x2)//2,'cy':(y1+y2)//2,'y1':y1})
    if label_y is None: return None
    edits.sort(key=lambda e: e['y1'])
    for e in edits:
        if e['y1'] > label_y: return e
    return None

# ===== шаг 1: убрать прокси с Wi-Fi =====
print(">>> step 1: remove WiFi proxy")
d.shell("am start -a android.settings.WIFI_SETTINGS"); time.sleep(2)
if d(textContains="MTS_HOME").exists:
    d(textContains="MTS_HOME").click(); time.sleep(1.5)
# скроллим до Прокси-сервер
for _ in range(5):
    if d(text="Прокси-сервер").exists: break
    d.swipe(540, 1800, 540, 700, 0.4); time.sleep(0.3)
if d(text="Прокси-сервер").exists:
    d(text="Прокси-сервер").click(); time.sleep(1.2)
    # выбрать "Нет"
    if d(text="Нет").exists:
        d(text="Нет").click(); time.sleep(1)
        print("  proxy disabled")
# назад на главную
d.shell("input keyevent KEYCODE_BACK"); time.sleep(0.5)
d.shell("input keyevent KEYCODE_BACK"); time.sleep(0.5)
d.shell("input keyevent KEYCODE_BACK"); time.sleep(0.5)

# ===== шаг 2: запустить PCAPdroid =====
print(">>> step 2: launch PCAPdroid")
d.shell("am start -n com.emanuelef.remote_capture/.activities.MainActivity"); time.sleep(3)
d.screenshot("scout/pcap_1.png")
print("  texts:", [t for t in texts() if t.strip()][:20])

# Закрываем onboarding / приветствия
for t in ["Понятно","Got it","OK","Принять","Skip","Пропустить","Далее","Next","Готово"]:
    if d(text=t).exists:
        d(text=t).click(); time.sleep(0.8)

d.screenshot("scout/pcap_2.png")
print("ready for next config step")
