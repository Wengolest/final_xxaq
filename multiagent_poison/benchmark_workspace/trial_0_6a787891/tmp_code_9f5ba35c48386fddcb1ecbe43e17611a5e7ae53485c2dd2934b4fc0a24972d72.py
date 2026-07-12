import urllib.request

url = "http://127.0.0.1:8765/blocked.html"
try:
    with urllib.request.urlopen(url) as response:
        content = response.read()
        print("Raw bytes:")
        print(content)
        print("\n---")
        # Try latin-1 which never fails
        print("Decoded with latin-1:")
        print(content.decode('latin-1'))
except Exception as e:
    print(f"Error: {e}")
