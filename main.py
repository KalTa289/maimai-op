import subprocess
from pathlib import Path

file_path = Path("MASTER.json")
if file_path.is_file():
    print("Data found. Overwrite with new data? (Y/N)")
    choice = input().lower()
    if choice == "y":
        subprocess.run(["python", "sync.py"])
else:
    print("Data not found. Automatically fetching data...")
    subprocess.run(["python", "sync.py"])

subprocess.run(["python", "calculate.py"])