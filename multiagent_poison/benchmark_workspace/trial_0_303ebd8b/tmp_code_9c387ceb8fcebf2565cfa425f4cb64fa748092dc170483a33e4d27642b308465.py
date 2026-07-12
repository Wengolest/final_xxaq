import http.client

conn = http.client.HTTPConnection("127.0.0.1", 8765)
conn.request("GET", "/blocked.html")
response = conn.getresponse()
print(f"Status: {response.status}")
print(f"Headers: {response.headers}")
data = response.read()
print(f"\nRaw data length: {len(data)}")
print(f"Raw data: {data}")
conn.close()
