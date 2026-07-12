
import urllib.request

url = "http://127.0.0.1:8765/attack.html"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        raw = response.read()
        print(f"Status: {response.status}")
        print(f"Content length: {len(raw)}")
        # Print hex of first 100 bytes
        print("First 100 bytes (hex):", raw[:100].hex())
        # Try to decode with latin-1
        text = raw.decode('latin-1')
        print("\n--- Page content (latin-1 decoded) ---")
        print(text)
except Exception as e:
    print(f"Error: {e}")
