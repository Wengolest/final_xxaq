import urllib.request

url = "http://127.0.0.1:8765/blocked.html"
try:
    with urllib.request.urlopen(url) as response:
        content = response.read()
        print("Raw bytes:")
        print(content)
        print("\n---")
        # Try to decode with different encodings
        for enc in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                decoded = content.decode(enc)
                print(f"\nDecoded with {enc}:")
                print(decoded)
            except:
                print(f"Failed to decode with {enc}")
except Exception as e:
    print(f"Error: {e}")
