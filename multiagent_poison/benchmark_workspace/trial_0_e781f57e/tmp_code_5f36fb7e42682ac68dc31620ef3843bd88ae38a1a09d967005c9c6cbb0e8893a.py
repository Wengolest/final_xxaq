
import urllib.request
url = "http://127.0.0.1:8765/attack.html"
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
raw = response.read()
open('attack_output.txt','wb').write(raw)
print("OK")
