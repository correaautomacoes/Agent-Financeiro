import urllib.request
try:
    resp = urllib.request.urlopen('http://localhost:8501', timeout=5)
    print(resp.getcode())
    print(resp.read(200).decode('utf-8', 'ignore'))
except Exception as e:
    print('ERROR', type(e).__name__, e)
