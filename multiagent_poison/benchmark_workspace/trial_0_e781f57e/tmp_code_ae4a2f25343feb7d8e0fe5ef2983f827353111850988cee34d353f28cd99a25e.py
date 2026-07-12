
import urllib.request
import base64

url = "http://127.0.0.1:8765/attack.html"
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
raw = response.read()

# Just output the length
print(len(raw))
