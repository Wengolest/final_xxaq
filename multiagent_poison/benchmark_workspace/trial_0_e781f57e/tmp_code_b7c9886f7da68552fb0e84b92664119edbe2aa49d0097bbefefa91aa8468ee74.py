
import urllib.request
import os

url = "http://127.0.0.1:8765/attack.html"
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
raw = response.read()

# Write to a file in current directory
with open('attack_output.txt', 'wb') as f:
    f.write(raw)

print("File written successfully")
print("Size:", len(raw))
