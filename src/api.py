import os

from flask import Flask, request
from google_auth_oauthlib.flow import InstalledAppFlow
from waitress import serve
from werkzeug.middleware.proxy_fix import ProxyFix

print("api: started")

# 環境変数から設定を取得
YOUTUBE_CLIENT_SECRET_FILE = os.environ["YOUTUBE_CLIENT_SECRET_FILE"]
YOUTUBE_TOKEN_PATH = os.environ["YOUTUBE_TOKEN_PATH"]

# Flask アプリの初期化
flask_app = Flask(__name__)

# Set environment variable to allow insecure transport for OAuthlib
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Apply ProxyFix middleware
flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)


# YouTube API の認証
@flask_app.route("/usercallback")
def usercallback():
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            YOUTUBE_CLIENT_SECRET_FILE,
            ["https://www.googleapis.com/auth/youtube.upload"],
        )
        flow.redirect_uri = "https://ktak.dev/slack-bot-auth/usercallback"
        flow.fetch_token(authorization_response=request.url)

        # Save the credentials for the next run
        credentials = flow.credentials
        with open(YOUTUBE_TOKEN_PATH, "w") as token:
            token.write(credentials.to_json())
        return "Authorization successful"

    except Exception as e:
        print(e)
        return f"Authorization failed: {e!r}"


if __name__ == "__main__":
    serve(flask_app, host="localhost", port=8001)
