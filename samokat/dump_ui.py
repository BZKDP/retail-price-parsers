# -*- coding: utf-8 -*-
import uiautomator2 as u2, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
d = u2.connect()
print('focus:', d.shell('dumpsys window | grep mCurrentFocus').output[:200])
import xml.etree.ElementTree as ET
h = d.dump_hierarchy()
root = ET.fromstring(h)
for n in root.iter('node'):
    t = n.get('text','')
    desc = n.get('content-desc','')
    if t.strip() and len(t) < 100:
        cls = n.get('class','').split('.')[-1]
        clk = n.get('clickable','')
        b = n.get('bounds','')
        sel = n.get('selected','')
        print(f'  {cls:15s} clk={clk} sel={sel} text={t!r} b={b}')
