import http.client
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='latin-1')

conn = http.client.HTTPConnection("127.0.0.1", 8765)
conn.request("GET", "/blocked.html")
response = conn.getresponse()
print("Status:", response.status, response.reason)
print("Headers:", dict(response.getheaders()))
data = response.read()
print("Data length:", len(data))
# Write to file
with open("/tmp/blocked.html", "wb") as f:
    f.write(data)
print("Saved to file")
conn.close()
