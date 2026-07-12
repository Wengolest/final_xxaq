import subprocess

# Check available tools
for cmd in ["curl", "wget", "nc", "telnet"]:
    result = subprocess.run(["which", cmd], capture_output=True)
    print(f"{cmd}: {result.stdout.decode('latin-1').strip() or 'not found'}")
