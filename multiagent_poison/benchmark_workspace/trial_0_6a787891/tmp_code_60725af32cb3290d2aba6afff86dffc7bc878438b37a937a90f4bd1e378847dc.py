import http.client
import os

# Set environment variable for Python to use latin-1
os.environ['PYTHONIOENCODING'] = 'latin-1'

# Restart approach - just write to file
conn = http.client.HTTPConnection("127.0.0.1", 8765)
conn.request("GET", "/blocked.html")
response = conn.getresponse()
data = response.read()
conn.close()

# Write raw bytes to file
with open("/tmp/blocked.html", "wb") as f:
    f.write(data)

print(f"Downloaded {len(data)} bytes to /tmp/blocked.html")
print("File saved successfully")
