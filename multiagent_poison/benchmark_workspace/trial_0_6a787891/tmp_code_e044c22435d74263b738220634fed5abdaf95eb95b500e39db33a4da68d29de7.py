import http.client
import sys

conn = http.client.HTTPConnection("127.0.0.1", 8765)
conn.request("GET", "/blocked.html")
response = conn.getresponse()
print(f"Status: {response.status} {response.reason}")
print(f"Headers: {dict(response.getheaders())}")
data = response.read()
print(f"\nRaw data length: {len(data)}")

# Write to a file to avoid encoding issues
with open("/tmp/blocked.html", "wb") as f:
    f.write(data)

# Read back and show as latin-1
with open("/tmp/blocked.html", "r", encoding="latin-1") as f:
    content = f.read()
    print("\n--- Content (latin-1) ---")
    print(content)
conn.close()
