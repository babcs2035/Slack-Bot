from dotenv import load_dotenv
import subprocess

load_dotenv()

print("main: Bot started")

subprocess.Popen(["python3", "-u", "src/UTOL.py"])
subprocess.Popen(["python3", "-u", "src/MF.py"])
subprocess.Popen(["python3", "-u", "src/video-backup.py"])

print("main: Bot initialized")

input()
