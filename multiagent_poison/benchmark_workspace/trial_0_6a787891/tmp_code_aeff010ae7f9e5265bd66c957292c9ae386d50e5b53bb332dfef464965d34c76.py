import http.client

conn = http.client.HTTPConnection("127.0.0.1", 8765)
conn.request("GET", "/blocked.html")
response = conn.getresponse()
print(f"Status: {response.status} {response.reason}")
print(f"Headers: {dict(response.getheaders())}")
data = response.read()
print(f"\nRaw data length: {len(data)}")
# Print first 200 bytes as hex and as latin-1
print(f"\nFirst 200 bytes (hex): {data[:200].hex()}")
print(f"\nFirst 200 bytes (latin-1): {data[:200].decode('latin-1')}")
conn.close()
