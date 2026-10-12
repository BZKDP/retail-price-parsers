import os
LAN_IP = os.environ.get("PROXY_HOST_LAN", "192.168.0.100")  # IP телефона/ПК в LAN, куда указывает прокси Wi-Fi
import uiautomator2 as u2
import time

d = u2.connect()

# Поле "Имя хоста"
host_field = d(text="proxy.example.com") or d(textContains="proxy.example")
if host_field.exists:
    host_field.click()
    time.sleep(0.5)
    d.clear_text()
    d.send_keys(LAN_IP)
    print(f"host: {LAN_IP}")
time.sleep(0.5)
d.press("back")  # скрыть клавиатуру
time.sleep(0.5)

# Скроллим вниз чтобы увидеть поле порта
for _ in range(3):
    if d(text="8080").exists or d(text="Порт").exists or d(text="Port").exists:
        break
    d.swipe(540, 1800, 540, 600, 0.4)
    time.sleep(0.5)

d.screenshot("scout/scroll_port.png")
import re
hier = d.dump_hierarchy()
# найдём все EditText и их подсказки
edits_re = re.findall(r'<node[^>]*class="android\.widget\.EditText"[^>]*hint="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', hier)
print(f"EditText with hints: {edits_re}")

# Найдём поле "8080" (это placeholder для порта)
port_field = d(text="8080") or d(textContains="8080") or d(textContains="порт")
print("port field exists:", port_field.exists)
if port_field.exists:
    port_field.click()
    time.sleep(0.5)
    d.clear_text()
    d.send_keys("8080")
    print("port: 8080")
time.sleep(0.5)
d.press("back")
time.sleep(0.5)
d.screenshot("scout/filled.png")

# Сохранить
for txt in ["Сохранить", "Save", "ОК", "OK", "Готово", "Done"]:
    e = d(text=txt)
    if e.exists:
        e.click(); print(f"saved via '{txt}'"); break
time.sleep(2)
d.screenshot("scout/saved.png")
