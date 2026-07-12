import os
# Try using os.system to run curl and save to file
os.system("curl -s http://127.0.0.1:8765/blocked.html -o /tmp/blocked_output.html 2>/tmp/curl_err.txt")
print("Done")
