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

# Write to file
with open("/tmp/attack_response.bin", "wb") as f:
    f.write(response)

print("Written to file. Length:", len(response))
print("First 100 bytes hex:", response[:100].hex())
