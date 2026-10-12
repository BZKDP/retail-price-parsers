import urllib.request, json
d = json.loads(urllib.request.urlopen('https://ipinfo.io/json', timeout=10).read())
print('IP:', d.get('ip'), 'region:', d.get('region'), 'country:', d.get('country'))
