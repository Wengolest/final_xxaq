
import urllib.request

url = "http://127.0.0.1:8765/attack.html"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        raw = response.read()
        print(f"Status: {response.status}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Content length: {len(raw)}")
        print(f"First 200 bytes hex: {raw[:200].hex()}")
        print(f"First 200 bytes repr: {raw[:200]}")
except Exception as e:
    print(f"Error: {e}")
