import requests
import json
import os
from pathlib import Path
from datetime import datetime
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler(
    executors={
        "threadpool": ThreadPoolExecutor(max_workers=1),
        "processpool": ProcessPoolExecutor(max_workers=1),
    }
)
print("🟢 expo: started")

# --- Configuration ---
API_URL = "https://ticket.expo2025.or.jp/api/d/schedules/2025/6"
COOKIE = os.environ["EXPO_COOKIE"]
SLACK_WEBHOOK_URL = os.environ["EXPO_SLACK_WEBHOOK_URL"]
TARGET_DAYS = ["19", "20"]
TARGET_TIME = "0700"
STATE_FILE = Path("previous_state.json")

headers = {
    "Cookie": COOKIE,
    "User-Agent": "Mozilla/5.0",
}

def notify_slack_error(error_msg):
    if not SLACK_WEBHOOK_URL:
        print(f"⚠️ Slack webhook URL not configured. Cannot send error notification.")
        return
    message = {
        "text": f"❗️ *EXPO Reservation Monitor Error* ❗️\n```{error_msg}```\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=message)
        if response.ok:
            print(f"✅ [{datetime.now()}] Sent error notification to Slack")
        else:
            print(f"❌ [{datetime.now()}] Failed to send error notification to Slack: {response.status_code} {response.text}")
    except Exception as ex:
        print(f"❌ [{datetime.now()}] Exception while sending error notification: {ex}")

def fetch_schedule():
    print(f"🔄 [{datetime.now()}] Fetching schedule: {API_URL}")
    response = requests.get(API_URL, headers=headers)
    response.raise_for_status()
    print(f"✅ [{datetime.now()}] Successfully fetched schedule")
    return response.json()

def extract_states(data):
    print(f"🔍 [{datetime.now()}] Extracting status for target days...")
    result = {}
    for day in TARGET_DAYS:
        try:
            time_state = data["states"][day]["1"][TARGET_TIME]["time_state"]
            result[day] = time_state
            print(f"  📅 June {day} at 07:00: {time_state}")
        except KeyError:
            result[day] = None
            print(f"  ⚠️ June {day} at 07:00: No information")
    return result

def load_previous():
    if STATE_FILE.exists():
        print(f"📂 [{datetime.now()}] Loading previous state from: {STATE_FILE}")
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    print(f"ℹ️ [{datetime.now()}] No previous state file found. First run or state not yet saved.")
    return {}

def save_current(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    print(f"💾 [{datetime.now()}] Current state saved to: {STATE_FILE}")

def notify_slack(changes):
    print(f"📣 [{datetime.now()}] Change detected. Sending Slack notification...")
    message = {
        "text": f"🎟 *EXPO reservation status changed* ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
                + "\n".join(
                    f"・June {day} at 07:00 changed from `{before}` to `{after}`"
                    for day, (before, after) in changes.items()
                )
    }
    response = requests.post(SLACK_WEBHOOK_URL, json=message)
    if response.ok:
        print(f"✅ [{datetime.now()}] Slack notification sent successfully")
    else:
        print(f"❌ [{datetime.now()}] Failed to send Slack notification: {response.status_code} {response.text}")

def main():
    print(f"\n🕒 ===== EXPO Reservation Monitor Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    try:
        data = fetch_schedule()
        current = extract_states(data)
        previous = load_previous()
        changes = {}

        for day in TARGET_DAYS:
            before = previous.get(day)
            after = current.get(day)
            if before is not None and after is not None and before != after:
                changes[day] = (before, after)
                print(f"🔔 [{datetime.now()}] Change detected: June {day} at 07:00 `{before}` → `{after}`")

        if changes:
            notify_slack(changes)
        else:
            print(f"✅ [{datetime.now()}] No changes detected. Skipping notification.")

        save_current(current)
    except Exception as e:
        error_msg = f"❗️ [{datetime.now()}] Error occurred: {e}"
        print(error_msg)
        notify_slack_error(error_msg)

    print(f"🕒 ===== EXPO Reservation Monitor Finished {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")

if __name__ == "__main__":
    try:
        print("🚀 expo: Main execution started")
        main()
    except Exception as e:
        error_msg = "⚠️ expo: __main__ error: " + str(e)
        print(error_msg)
        notify_slack_error(error_msg)

@sched.scheduled_job(
    "cron", hour='*', minute="*", second='0', executor="threadpool", misfire_grace_time=60 * 60
)
def scheduled_job():
    print("📅 expo: ----- main started -----")
    main()
    print("✅ expo: ----- main done -----")


sched.start()
print("🟢 expo: initialized")
