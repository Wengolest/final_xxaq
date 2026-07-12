import socket

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
print(f"Total bytes received: {len(data)}")
print(data)
