import os
import json
import psutil
import platform
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

print("status: Bot started")


def sendMessageToSlack(channel, message, attachments=json.dumps([])):
    try:
        client = WebClient(token=os.environ["SLACK_TOKEN"])
        client.chat_postMessage(channel=channel, text=message, attachments=attachments)
    except Exception as e:
        print("sendMessageToSlack(): " + str(e))
    else:
        print("sendMessageToSlack(): successfully sent message to " + channel)


def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor


def sendStatus():
    message = "*<<System Info>>*\n"
    uname = platform.uname()
    message += f"*System*\t{uname.system}\n"
    message += f"*Node Name*\t{uname.node}\n"
    message += f"*Release*\t{uname.release}\n"
    message += f"*Version*\t{uname.version}\n"
    message += f"*Machine*\t{uname.machine}\n"
    message += f"*Processor*\t{uname.processor}\n"

    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    message += f"*Boot Time*\t{bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}\n"

    cpufreq = psutil.cpu_freq()
    message += f"*CPU*\t{psutil.cpu_percent()}% {cpufreq.current:.2f}Mhz\n"

    svmem = psutil.virtual_memory()
    message += f"*Memory*\t{get_size(svmem.used)}/{get_size(svmem.total)} ({svmem.percent}%)\n"

    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        message += f"*Disk*\t{partition.device} {get_size(partition_usage.used)}/{get_size(partition_usage.total)} ({partition_usage.percent}%)\n"

    sendMessageToSlack("#status", message)


print("status: Bot initialized")
