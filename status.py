import os
import json
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

sched = BlockingScheduler(
    executors={
        "threadpool": ThreadPoolExecutor(max_workers=5),
        "processpool": ProcessPoolExecutor(max_workers=1),
    }
)

print("status: Bot started")


def sendMessageToSlack(channel, message, attachments=json.dumps([])):
    try:
        client = WebClient(token=os.environ["SLACK_TOKEN"])
        client.chat_postMessage(channel=channel, text=message, attachments=attachments)
    except Exception as e:
        print("sendMessageToSlack(): " + str(e))
    else:
        print("sendMessageToSlack(): successfully sent message to " + channel)


def sendStatus():
    sendMessageToSlack("#general", "Bot is running")


@sched.scheduled_job("interval", minutes=1, executor="threadpool")
def scheduled_job():
    print("----- sendStatus started -----")
    sendStatus()
    print("----- sendStatus done -----")


sched.start()
print("status: Bot initialized")
