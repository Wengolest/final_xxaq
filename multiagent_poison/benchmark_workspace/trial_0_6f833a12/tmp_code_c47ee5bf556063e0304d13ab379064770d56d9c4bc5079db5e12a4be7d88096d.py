import os

# Check if the base directory exists
base = r"benchmark_workspace"
print("Exists:", os.path.exists(base))
print("Contents:", os.listdir(base))
