import subprocess
# Use shell to run curl and save to file
subprocess.run("curl -s http://127.0.0.1:8765/blocked.html > /tmp/blocked_output.html 2>/tmp/curl_err.txt", shell=True)
print("curl done")
