from dotenv import load_dotenv
import subprocess

load_dotenv()

print("main: started")

subprocess.Popen(["python3", "-u", "src/UTOL.py"])
subprocess.Popen(["python3", "-u", "src/MF.py"])
subprocess.Popen(["python3", "-u", "src/video-backup.py"])
subprocess.Popen(["python3", "-u", "src/api.py"])

print("main: initialized")

input()
