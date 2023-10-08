from dotenv import load_dotenv
import subprocess

load_dotenv()

print("main: Bot started")

subprocess.Popen(["python3", "-u", "src/LMS.py"])

print("main: Bot initialized")

input()
