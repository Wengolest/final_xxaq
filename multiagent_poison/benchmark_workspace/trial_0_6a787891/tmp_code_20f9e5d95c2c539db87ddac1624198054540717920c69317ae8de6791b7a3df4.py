import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", 8765))
request = b"GET /blocked.html HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nConnection: close\r\n\r\n"
s.sendall(request)

# Read header first
header = b""
while True:
    c = s.recv(1)
    header += c
    if header.endswith(b"\r\n\r\n"):
        break

print("Header received, length:", len(header))
# Now read body
body = b""
while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    body += chunk
s.close()

print("Body length:", len(body))
with open("/tmp/blocked.html", "wb") as f:
    f.write(body)
print("Saved to file")
