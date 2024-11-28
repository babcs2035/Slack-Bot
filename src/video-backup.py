import os
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 環境変数から設定を取得
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_CLIENT_SECRET_FILE = os.environ["YOUTUBE_CLIENT_SECRET_FILE"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]

# Slack アプリの初期化
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# Google Sheets API の認証
creds = ServiceAccountCredentials.from_json_keyfile_name(
    GOOGLE_SERVICE_ACCOUNT_FILE,
    [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ],
)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# YouTube API の認証
credentials = service_account.Credentials.from_service_account_file(
    YOUTUBE_CLIENT_SECRET_FILE
)
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


def terminate(message):
    print(f"video-backup: {message}")
    print("---------------- video-backup ended ----------------")


@app.event("message")
def handle_message_events(body, say):
    print("---------------- video-backup started ----------------")

    try:
        event = body.get("event", {})
        if event.get("subtype") in ["message_deleted", "message_changed"]:
            terminate("Invalid event.subtype")
            return

        if not (
            event.get("type") == "message"
            and event.get("user") != os.environ["BOT_USER"]
        ):
            terminate("Invalid event")
            return

        channel_id = event.get("channel")
        thread_ts = event.get("ts")

        if channel_id != SLACK_CHANNEL_ID:
            terminate("Invalid channelId")
            return

        video = find_latest_video(event)
        if not video:
            post_message_to_slack(channel_id, thread_ts, "*Video not found*")
            terminate("Video not found")
            return

        if check_if_video_exists(video["name"]):
            post_message_to_slack(
                channel_id, thread_ts, "*This video has already been uploaded*"
            )
            terminate("This video has already been uploaded")
            return

        video_filename = download_slack_file(video["url"])
        upload_response = upload_video_to_youtube(
            video_filename, video["name"], event.get("text", "")
        )

        if upload_response.get("id"):
            video_url = f"https://www.youtube.com/watch?v={upload_response['id']}"
            post_message_to_slack(
                channel_id, thread_ts, f"*Successfully uploaded video*\n{video_url}"
            )
            write_data = [
                str(datetime.now()),
                video["name"],
                video["url"],
                event.get("text", ""),
                video_url,
                "succeeded",
            ]
        else:
            post_message_to_slack(
                channel_id, thread_ts, f"*Failed to upload video*\n{upload_response}"
            )
            write_data = [
                str(datetime.now()),
                video["name"],
                video["url"],
                event.get("text", ""),
                "",
                "failed",
            ]

        sheet.append_row(write_data)
        terminate("terminated")
    except Exception as e:
        post_message_to_slack(channel_id, thread_ts, f"*Error*\n{e}")
        terminate(f"video-backup: Error: {e}")


def find_latest_video(message):
    extensions = [".mov", ".MOV", ".mp4", ".MP4"]
    for file in message.get("files", []):
        for ext in extensions:
            if file["url_private"].endswith(ext):
                return {"url": file["url_private"], "name": file["name"]}
    return None


def download_slack_file(file_url):
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()

    ext = file_url.split(".")[-1]
    with open(f"video.{ext}", "wb") as f:
        f.write(response.content)
    print(f"video-backup: Downloaded file from {file_url}")
    return f"video.{ext}"


def upload_video_to_youtube(filename, title, description):
    body = {
        "snippet": {
            "title": title,
            "description": description,
        },
        "status": {
            "privacyStatus": "private",
        },
    }
    media = MediaFileUpload(filename, mimetype="video/*", resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = request.execute()
    return response


def check_if_video_exists(title):
    records = sheet.get_all_records()
    for record in records:
        if record["Title"] == title and record["Status"] == "succeeded":
            print(f'video-backup: Found existing video with title: "{title}"')
            return True
    return False


def post_message_to_slack(channel_id, thread_ts, message):
    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        response = client.chat_postMessage(
            channel=channel_id, thread_ts=thread_ts, text=message
        )
    except SlackApiError as e:
        print(f"video-backup: Failed to post message to Slack: {e.response['error']}")


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 5000)))
