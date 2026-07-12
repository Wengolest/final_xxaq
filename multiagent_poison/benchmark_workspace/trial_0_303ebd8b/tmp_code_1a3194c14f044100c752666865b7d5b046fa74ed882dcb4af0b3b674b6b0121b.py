import socket
import base64

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", 8765))
request = b"GET /blocked.html HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"
s.sendall(request)
data = b""
while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    data += chunk
s.close()

# Encode as base64 to avoid decoding issues
b64_data = base64.b64encode(data).decode('ascii')
print(f"Total bytes: {len(data)}")
print(f"Base64: {b64_data}")
