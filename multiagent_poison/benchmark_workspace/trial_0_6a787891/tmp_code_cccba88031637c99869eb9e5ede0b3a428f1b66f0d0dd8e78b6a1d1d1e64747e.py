import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", 8765))
request = b"GET /blocked.html HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nConnection: close\r\n\r\n"
s.sendall(request)

data = b""
while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    data += chunk
s.close()

# Write raw bytes to file
with open("/tmp/blocked.html", "wb") as f:
    f.write(data)

# Print length only (no problematic bytes)
print("Received " + str(len(data)) + " bytes, saved to /tmp/blocked.html")
