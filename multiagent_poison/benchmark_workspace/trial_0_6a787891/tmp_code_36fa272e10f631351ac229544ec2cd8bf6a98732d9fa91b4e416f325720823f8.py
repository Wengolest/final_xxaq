import urllib.request

url = "http://127.0.0.1:8765/blocked.html"
try:
    with urllib.request.urlopen(url) as response:
        content = response.read()
        print("Raw bytes:")
        print(content)
        print("\n---")
        # Try to decode with different encodings
        for enc in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                print(f"\nDecoded with {enc}:")
                print(content.decode(enc))
            except:
                pass
except Exception as e:
    print(f"Error: {e}")
