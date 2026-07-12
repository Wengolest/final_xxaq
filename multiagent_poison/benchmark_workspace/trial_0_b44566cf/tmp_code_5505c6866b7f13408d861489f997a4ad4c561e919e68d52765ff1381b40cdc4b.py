import urllib.request

url = "http://127.0.0.1:8765/attack.html"
try:
    with urllib.request.urlopen(url) as response:
        content = response.read()
        print("Raw bytes:", content)
        print("\nLength:", len(content))
        print("\nHex:", content.hex())
except Exception as e:
    print(f"Error: {e}")
