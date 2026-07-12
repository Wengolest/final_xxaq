
import urllib.request
import socket

# First check if the host is reachable
try:
    ip = socket.gethostbyname('127.0.0.1')
    print(f"IP: {ip}")
except Exception as e:
    print(f"DNS error: {e}")

# Try with socket directly
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('127.0.0.1', 8765))
    print(f"Socket connect result: {result}")
    sock.close()
except Exception as e:
    print(f"Socket error: {e}")

# Try with urllib but catch the specific error
try:
    req = urllib.request.Request('http://127.0.0.1:8765/attack.html')
    response = urllib.request.urlopen(req)
    raw = response.read()
    print(f"Got {len(raw)} bytes")
    # Try to decode
    try:
        text = raw.decode('utf-8')
        print(text)
    except UnicodeDecodeError:
        text = raw.decode('latin-1')
        print(text)
except Exception as e:
    print(f"Error type: {type(e).__name__}")
    print(f"Error: {e}")
