# -*- coding: utf-8 -*-
import uiautomator2 as u2, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
d = u2.connect()
d.shell('am start -n com.emanuelef.remote_capture/.activities.MainActivity'); time.sleep(2)
# Кликаем по СОСТОЯНИЕ
d(text='СОСТОЯНИЕ').click(); time.sleep(1.5)
d.screenshot('scout/state_tab.png')
import xml.etree.ElementTree as ET
h = d.dump_hierarchy()
root = ET.fromstring(h)
print('focus:', d.shell('dumpsys window | grep mCurrentFocus').output[:200])
for n in root.iter('node'):
    t = n.get('text','')
    desc = n.get('content-desc','')
    if t.strip() and len(t) < 100:
        cls = n.get('class','').split('.')[-1]
        clk = n.get('clickable','')
        b = n.get('bounds','')
        print(f'  {cls:15s} clk={clk} text={t!r} b={b}')
