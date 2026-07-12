import urllib.request

url = "http://127.0.0.1:8765/attack.html"
try:
    with urllib.request.urlopen(url) as response:
        content = response.read()
        print("Raw bytes:", content[:200])
        # Try different encodings
        for enc in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                decoded = content.decode(enc)
                print(f"\n--- Decoded with {enc} ---")
                print(decoded)
                break
            except:
                continue
except Exception as e:
    print(f"Error: {e}")
