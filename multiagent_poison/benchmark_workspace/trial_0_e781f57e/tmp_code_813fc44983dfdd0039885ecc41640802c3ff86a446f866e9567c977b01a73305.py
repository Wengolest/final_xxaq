
import urllib.request
import sys

url = "http://127.0.0.1:8765/attack.html"
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
raw = response.read()

# Just print the hex representation
print("Content length:", len(raw))
print("First 200 bytes hex:", raw[:200].hex())
print()
# Print as repr to avoid encoding issues
print("First 200 bytes repr:", repr(raw[:200]))
