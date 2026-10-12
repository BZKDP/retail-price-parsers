import socket, urllib.request
try:
    print('resolve:', socket.gethostbyname('api.samokat.ru'))
except Exception as e:
    print('resolve fail:', e)
try:
    r = urllib.request.urlopen('https://api.samokat.ru/', timeout=5)
    print('http ok:', r.status)
except Exception as e:
    print('http fail:', e)
