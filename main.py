# import
import subprocess
from dotenv import load_dotenv
load_dotenv()

print("main: Bot started")

subprocess.Popen(["python", "-u", "ITC-LMS.py"])

print("main: Bot initialized")
