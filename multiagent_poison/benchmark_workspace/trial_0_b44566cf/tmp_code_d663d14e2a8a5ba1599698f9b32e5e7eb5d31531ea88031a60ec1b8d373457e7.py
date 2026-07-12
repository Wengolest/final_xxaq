import urllib.request

url = "http://127.0.0.1:8765/attack.html"
try:
    with urllib.request.urlopen(url) as response:
        content = response.read().decode('utf-8')
        print(content)
except Exception as e:
    print(f"Error: {e}")
