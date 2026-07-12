
import urllib.request

url = "http://127.0.0.1:8765/attack.html"
try:
    with urllib.request.urlopen(url) as response:
        html_content = response.read()
        print("Raw bytes (first 500):", html_content[:500])
        print("\n--- Trying latin-1 encoding ---")
        print(html_content.decode('latin-1'))
except Exception as e:
    print(f"Error: {e}")
