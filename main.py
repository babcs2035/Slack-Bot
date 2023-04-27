import subprocess
from dotenv import load_dotenv
load_dotenv()

print("main: Bot started")

subprocess.Popen(["python3", "-u", "ITC-LMS.py"])
subprocess.Popen(["python3", "-u", "status.py"])

print("main: Bot initialized")
