
import urllib.request

url = "http://127.0.0.1:8765/attack.html"
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
raw = response.read()

# Write to a file
with open('/tmp/attack_page.txt', 'wb') as f:
    f.write(raw)

print(f"Saved {len(raw)} bytes to /tmp/attack_page.txt")
print("First 50 bytes hex:", raw[:50].hex())
