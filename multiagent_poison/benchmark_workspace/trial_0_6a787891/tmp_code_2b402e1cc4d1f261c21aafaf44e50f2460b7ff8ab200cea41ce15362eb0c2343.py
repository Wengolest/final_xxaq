import http.client
import sys
import io

# Force stdout to use latin-1
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='latin-1')

conn = http.client.HTTPConnection("127.0.0.1", 8765)
conn.request("GET", "/blocked.html")
response = conn.getresponse()
print(f"Status: {response.status} {response.reason}")
print(f"Headers: {dict(response.getheaders())}")
data = response.read()
print(f"\nRaw data length: {len(data)}")

# Print the content
content = data.decode('latin-1')
print("\n--- Content ---")
print(content)
conn.close()
