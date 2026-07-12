import urllib.request

url = "http://127.0.0.1:8765/attack.html"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        content = response.read()
        # Print as repr to see the actual bytes
        print(repr(content))
except Exception as e:
    print(f"Error type:", type(e).__name__)
    print(f"Error:", e)
