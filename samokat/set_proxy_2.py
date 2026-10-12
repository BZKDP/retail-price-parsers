import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
import uiautomator2 as u2
import time

d = u2.connect()
# Тап на "Настройка вручную"
ok = d(text="Настройка вручную").click_exists(timeout=3) or d(text="Manual").click_exists(timeout=3)
print("manual clicked:", ok)
time.sleep(1.5)
d.screenshot("scout/manual.png")

# Должны появиться поля Hostname и Port
# Идём по дереву и ищем EditText
hier = d.dump_hierarchy()
import re
edits = re.findall(r'<node[^>]*class="android\.widget\.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', hier)
print(f"EditText fields: {len(edits)}")
for i, e in enumerate(edits):
    print(f"  edit {i}: {e}")

# заполним host и port
hosts = d(className="android.widget.EditText")
print(f"editables: {hosts.count}")
# часто на ColorOS поле hostname идёт первым, port вторым
if hosts.count >= 2:
    hosts[0].click(); time.sleep(0.3); hosts[0].clear_text(); hosts[0].send_keys(LAN_IP)
    print("host typed")
    hosts[1].click(); time.sleep(0.3); hosts[1].clear_text(); hosts[1].send_keys("8080")
    print("port typed")
time.sleep(1)
d.screenshot("scout/typed.png")

# нажимаем "Сохранить" / "Save" / "ОК"
for txt in ["Сохранить", "Save", "ОК", "OK"]:
    if d(text=txt).click_exists(timeout=2):
        print(f"clicked save: '{txt}'"); break
time.sleep(2)
d.screenshot("scout/saved.png")
