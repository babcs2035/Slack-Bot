import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
import status
from dotenv import load_dotenv
load_dotenv()

sched = BlockingScheduler(
    executors={
        'threadpool': ThreadPoolExecutor(max_workers=1),
        'processpool': ProcessPoolExecutor(max_workers=1)
    }
)

print("main: Bot started")


@sched.scheduled_job("cron", minute="0", hour="0", executor="threadpool")
def scheduled_job():
    print("----- sendStatus started -----")
    status.sendStatus()
    print("----- sendStatus done -----")


subprocess.Popen(["python3", "-u", "ITC-LMS.py"])

sched.start()
print("main: Bot initialized")
