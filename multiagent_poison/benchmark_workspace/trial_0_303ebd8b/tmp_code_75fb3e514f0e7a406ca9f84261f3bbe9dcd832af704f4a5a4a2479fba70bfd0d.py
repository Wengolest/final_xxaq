import urllib.request
import io

url = "http://127.0.0.1:8765/blocked.html"
try:
    with urllib.request.urlopen(url) as response:
        content = response.read()
        print("Raw bytes:")
        print(content)
        print("\n---")
        # Try latin-1 which can decode any byte
        decoded = content.decode('latin-1')
        print("Decoded with latin-1:")
        print(decoded)
except Exception as e:
    print(f"Error: {e}")
