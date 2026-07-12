import http.client

conn = http.client.HTTPConnection("127.0.0.1", 8765)
conn.request("GET", "/blocked.html")
response = conn.getresponse()
print(f"Status: {response.status} {response.reason}")
print(f"Headers: {dict(response.getheaders())}")
data = response.read()
print(f"\nRaw data length: {len(data)}")
print(f"Raw data: {data}")
print(f"\nDecoded latin-1: {data.decode('latin-1')}")
conn.close()
