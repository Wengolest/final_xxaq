import socket

host = "127.0.0.1"
port = 8765

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
sock.connect((host, port))

request = b"GET /attack.html HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nConnection: close\r\n\r\n"
sock.sendall(request)

response = b""
while True:
    try:
        data = sock.recv(4096)
        if not data:
            break
        response += data
    except:
        break

sock.close()

print("Raw response:")
print(repr(response))
print("\n--- Decoded (latin-1) ---")
print(response.decode('latin-1'))
