import os

path = r"benchmark_workspace\trial_0_6f833a12\content"
# Try to list with scandir
for entry in os.scandir(path):
    print(entry.name, entry.is_file(), entry.is_dir())
