
import urllib.request
import base64

url = "http://127.0.0.1:8765/attack.html"
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
raw = response.read()

# Base64 encode the content to avoid encoding issues
b64 = base64.b64encode(raw).decode('ascii')
print("BASE64_START")
print(b64)
print("BASE64_END")
print("LENGTH:", len(raw))
