import os
import threading
import time
import logging
from datetime import datetime  # Import datetime for current date
from dotenv import load_dotenv

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from data_fetcher import fetch_data_json, fetch_add_json
from data_manager import data_manager
from watched_pavilions import watched_pavilion_manager

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Slack Bot Token and App Token
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
# Channel ID for automatic notifications (e.g., pavilion status changes)
SLACK_EXPO_NOTIFICATION_CHANNEL_ID = os.environ.get(
    "SLACK_EXPO_NOTIFICATION_CHANNEL_ID"
)

# Initialize Slack App in Socket Mode
app = App(token=SLACK_BOT_TOKEN)

# Mapping for status codes to human-readable strings and emojis
STATUS_MAP = {
    2: "Unavailable ⛔️",
    1: "Limited ⚠️",
    0: "Available ✅",
}

# Mapping for status codes to colors
STATUS_COLOR_MAP = {
    2: "#E0BBE4",  # Soft Red/Pink for Unavailable
    1: "#FFD34F",  # Yellowish-Orange for Limited
    0: "#A5D6A7",  # Soft Green for Available
}


def get_status_text(status_code):
    """Converts status code to human-readable text with emoji."""
    return STATUS_MAP.get(status_code, f"Unknown Status ({status_code}) ❓")


def get_status_color(status_code):
    """Returns the color hex code for a given status."""
    return STATUS_COLOR_MAP.get(
        status_code, "#B0BEC5"
    )  # Light grey for unknown/default


def get_expo_ticket_link(pavilion_id, ids_list):
    """
    Constructs the specific Expo ticket link.
    Args:
        pavilion_id (str): The ID of the pavilion (event_id).
        ids_list (list): A list of user-specified IDs (e.g., ticket IDs).
    Returns:
        str: The constructed URL.
    """
    today_date_str = datetime.now().strftime(
        "%Y%m%d"
    )  # Format today's date as YYYYMMDD
    ids_param = ",".join(ids_list) if ids_list else ""  # Join IDs with comma

    # Base URL components
    base_url = "https://ticket.expo2025.or.jp/event_time/"
    params = {
        "id": ids_param,
        "event_id": pavilion_id,
        "screen_id": "108",
        "lottery": "5",
        "entrance_date": today_date_str,
    }

    # Construct query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items() if v])
    return f"{base_url}?{query_string}"


def send_slack_notification(
    text_message=None, blocks=None, attachments=None, channel_id=None, thread_ts=None
):
    """
    Sends a Slack message using Slack Bolt's web client.
    Args:
        text_message (str, optional): Fallback text message for clients that don't support blocks/attachments.
        blocks (list, optional): A list of Block Kit blocks.
        attachments (list, optional): A list of legacy Slack attachment dictionaries (used for color property).
        channel_id (str): The channel ID to send the message to. Required for notifications.
        thread_ts (str, optional): The timestamp of the parent message to reply to.
    """
    if not channel_id:
        logging.error(
            "Channel ID must be provided to send notifications via chat_postMessage."
        )
        return

    try:
        app.client.chat_postMessage(
            channel=channel_id,
            text=text_message,  # Fallback text
            blocks=blocks,  # Blocks are passed here, but `monitor_add_json` will not use them in this iteration.
            attachments=attachments,  # Attachments are passed here, used for color and simplified content.
            thread_ts=thread_ts,
        )
        logging.info(f"Slack notification sent to channel {channel_id}.")
    except Exception as e:
        logging.error(f"Failed to send Slack notification via chat_postMessage: {e}")


def monitor_data_json():
    """
    Monitors data.json every minute and reloads the full pavilion data.
    This also acts as a full refresh and consistency check.
    """
    logging.info("Starting data.json monitor thread.")
    while True:
        logging.info("Fetching data.json for full refresh...")
        new_data = fetch_data_json()
        if new_data:
            data_manager.load_initial_data(new_data)
        time.sleep(60)  # Fetch every 60 seconds


def monitor_add_json():
    """
    Monitors add.json every second and applies delta updates,
    then checks for changes in watched pavilions.
    """
    logging.info("Starting add.json monitor thread.")
    while True:
        updates = fetch_add_json()
        if updates:
            # Apply updates and get detected changes
            changes = data_manager.apply_updates(updates)

            # Check if any changes affect watched pavilions
            for code, time_changes in changes.items():
                if code in watched_pavilion_manager.get_watched_list():
                    pavilion_name = data_manager.get_pavilion_name(code)

                    # Get user's ticket IDs to build the specific link
                    # For simplicity, we'll use a generic placeholder or assume
                    # a common set of IDs for notification.
                    # A more complex bot would notify each user in a DM
                    # using their specific IDs, but for channel notification,
                    # we need a common approach.
                    # Let's fetch IDs from the user who last set them or a default.
                    # For a channel notification, we need a consistent set of IDs.
                    # For this implementation, we will use a dummy ID for the URL,
                    # as user-specific IDs in a public channel notification don't make sense.
                    # If this is for per-user DM, we'd iterate over users watching this pavilion.

                    # For now, we'll use a placeholder or assume a way to get a relevant ID list.
                    # Let's assume the bot itself might have default IDs for general notifications.
                    # Or, better: if a user is watching, maybe use *their* IDs if it's a DM.
                    # Since it's a channel notification, we'll use a placeholder or empty list for the URL's `id` param.

                    # If you want to use a specific user's IDs for the link in a public channel,
                    # you'd need to decide *whose* IDs to use. For now, we'll make 'id' param empty
                    # or you can set a default ID list in .env or config.

                    # Let's adjust get_expo_ticket_link to be callable with just pavilion_id for general notifications
                    # And use a hardcoded default ID for the link if none are set.
                    # Or, even better, if it's a channel notification, just leave the `id` param empty
                    # if no specific user's ID is contextually available.

                    # Updated: `get_expo_ticket_link` now takes optional user_id,
                    # and `monitor_add_json` will pass an empty list for channel notifications.
                    # Users can set their IDs, but the public notification link will not include them by default.
                    # If you want specific user IDs in the public notification,
                    # you need to determine which user's IDs to use.

                    # Pavilion ID is 'code' in our data
                    user_ticket_ids_for_link = watched_pavilion_manager.get_user_ticket_ids("U055AN8LWF6")
    current_expo_link = get_expo_ticket_link(
        pavilion_id=code, ids_list=user_ticket_ids_for_link
    )

                    for time_slot, (old_status, new_status) in time_changes.items():
                        # Only notify if the status has actually changed meaningfully
                        if old_status != new_status:
                            new_status_text = get_status_text(new_status)

                            # Determine color based on the new status
                            attachment_color = get_status_color(new_status)

                            # --- Construct the simple legacy attachment for status change notification ---
                            # As per the user's request, use this specific attachment format
                            notification_attachments = [
                                {
                                    "color": attachment_color,
                                    "title": f"{new_status_text[0]} {pavilion_name} ({code})",  # Title of the attachment
                                    "fields": [
                                        {
                                            "title": "Time Slot",
                                            "value": f"{time_slot[:2]}:{time_slot[2:]}",
                                            "short": True,
                                        },
                                        {
                                            "title": "Current Status",  # Only show current status as requested
                                            "value": new_status_text,
                                            "short": True,
                                        },
                                        {
                                            "title": "Book URL",  # New field for the booking link
                                            "value": f"<{current_expo_link}|Link>",
                                            "short": True,
                                        },
                                    ],
                                }
                            ]

                            send_slack_notification(
                                # text_message=f"Status update for {pavilion_name} at {time_slot[:2]}:{time_slot[2:]}",  # Fallback text
                                attachments=notification_attachments,
                                channel_id=SLACK_EXPO_NOTIFICATION_CHANNEL_ID,
                            )
        time.sleep(1)  # Fetch every 1 second


### Slack Command Handlers ###


@app.event("app_mention")
def handle_app_mention(say, body):
    """Responds to @bot mentions."""
    # Replies in thread
    say(
        thread_ts=body["event"]["ts"],
        text=f"Hello! I'm here to help you monitor Expo 2025 pavilion availability. Try `/help_expo` for commands. 🤖",
    )


@app.event("message")
def handle_message_events(body, logger, message):
    """
    Handles all 'message' events.
    This listener is added to prevent 'Unhandled request' warnings for messages
    that are not explicitly handled (e.g., bot_messages, channel messages without mention).
    It filters out messages posted by bots to avoid infinite loops.
    """
    # Check if the message is from a bot itself (including this bot)
    # or if it's a message type that typically doesn't need a direct response.
    if message.get("subtype") == "bot_message":
        logger.debug("Ignoring bot_message to prevent infinite loops.")
        return  # Do nothing for bot messages

    if "text" in message and app.client.auth_test()["user_id"] not in message.get(
        "text", ""
    ):
        logger.info(f"Unhandled non-bot message: {message.get('text')}")
    else:
        logger.debug(f"Unhandled message event: {body}")


@app.command("/help_expo")
def handle_help_command(ack, respond, command):
    """Provides help text for available commands."""
    ack()
    help_message_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Hello! I can help you monitor Expo 2025 pavilion availability. Here are my commands: 🤖",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "• `/list_all_expo` : Show a list of all known pavilions and their codes. 📋\n"
                "• `/search_expo [QUERY]` : Search for pavilions by name (e.g., `/search_expo 日本館`). 🔎\n"
                "• `/watch_expo [CODE]` : Add a pavilion to your watch list. (e.g., `/watch_expo HOH0`) 👀\n"
                "• `/unwatch_expo [CODE]` : Remove a pavilion from your watch list. (e.g., `/unwatch_expo HOH0`) 🚫\n"
                "• `/list_watched_expo` : Show pavilions you are currently watching. 🔔\n"
                "• `/set_ticket_ids [ID1,ID2,...]` : Set your personal ticket IDs for booking links. (e.g., `/set_ticket_ids 12345,67890`) 🎫\n"  # NEW COMMAND
                "• `/show_status_expo [CODE]` : Show the current availability status for a specific pavilion. (e.g., `/show_status_expo HOH0`) 📊\n"
                "I will notify you via Slack when the availability status of a watched pavilion changes! ✨",
            },
        },
    ]
    respond(
        blocks=help_message_blocks,
        response_type="in_channel",
        # thread_ts=command["event"]["ts"], # Removed for slash commands
    )


@app.command("/list_all_expo")
def list_all_pavilions(ack, respond, command):
    """Lists all available pavilions with their codes."""
    ack()
    pavilions_info = data_manager.get_all_pavilions_info()
    if not pavilions_info:
        respond(
            text="Sorry, I couldn't fetch the list of pavilions. Please try again later. 😟",
            response_type="ephemeral",
            # thread_ts=command["event"]["ts"], # Removed for slash commands
        )
        return

    # Sort by name for better readability
    pavilions_info.sort(key=lambda x: x["name"])

    message_blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Here are all the pavilions I know: 🏛️"},
        },
        {"type": "divider"},
    ]

    # Concatenate pavilion list into a single markdown block for length
    pavilion_list_text = ""
    MAX_PAVILIONS_DISPLAY = 50  # Limit to display in one message
    for i, p in enumerate(pavilions_info):
        if i >= MAX_PAVILIONS_DISPLAY:
            pavilion_list_text += f"\n_... and {len(pavilions_info) - i} more. Use `/search_expo` to find specific ones!_"
            break
        pavilion_list_text += f"• `{p['code']}`: {p['name']}\n"

    if pavilion_list_text:
        message_blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": pavilion_list_text}}
        )

    message_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\nUse `/watch_expo [CODE]` to start monitoring! 👀",
            },
        }
    )

    respond(
        blocks=message_blocks,
        response_type="in_channel",
        # thread_ts=command["event"]["ts"], # Removed for slash commands
    )


@app.command("/watch_expo")
def watch_pavilion(ack, respond, command):
    """Adds a pavilion to the watch list."""
    ack()
    args = command["text"].strip().split()
    if not args:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text="Please specify a pavilion code. Example: `/watch_expo HOH0` 🧐",
            response_type="ephemeral",
        )
        return

    code = args[0].upper()
    pavilion_name = data_manager.get_pavilion_name(code)
    if (
        not pavilion_name or pavilion_name == code
    ):  # Check if it's a valid known pavilion
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"Pavilion with code `{code}` not found. Please check `/list_all_expo` for valid codes. ❌",
            response_type="ephemeral",
        )
        return

    if watched_pavilion_manager.add_pavilion(code):
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"Successfully added *{pavilion_name}* (`{code}`) to your watch list! I'll notify you of availability changes. 🎉",
            response_type="in_channel",
        )
        logging.info(f"User added {code} to watch list.")
    else:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"*{pavilion_name}* (`{code}`) is already on your watch list. You'll be notified of changes! 😉",
            response_type="ephemeral",
        )


@app.command("/unwatch_expo")
def unwatch_pavilion(ack, respond, command):
    """Removes a pavilion from the watch list."""
    ack()
    args = command["text"].strip().split()
    if not args:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text="Please specify a pavilion code. Example: `/unwatch_expo HOH0` 🧐",
            response_type="ephemeral",
        )
        return

    code = args[0].upper()
    if watched_pavilion_manager.remove_pavilion(code):
        pavilion_name = data_manager.get_pavilion_name(code)
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"Removed *{pavilion_name}* (`{code}`) from your watch list. You will no longer receive notifications for it. 👋",
            response_type="in_channel",
        )
        logging.info(f"User removed {code} from watch list.")
    else:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"Pavilion with code `{code}` was not found in your watch list. Nothing to unwatch. 🤷‍♀️",
            response_type="ephemeral",
        )


@app.command("/list_watched_expo")
def list_watched_pavilions(ack, respond, command):
    """Lists pavilions currently being watched."""
    ack()
    watched_codes = watched_pavilion_manager.get_watched_list()
    if not watched_codes:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text="You are not currently watching any pavilions. Use `/watch_expo [CODE]` to add one! 🚀",
            response_type="ephemeral",
        )
        return

    message_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "You are currently watching these pavilions: 🔍",
            },
        },
        {"type": "divider"},
    ]

    watched_list_text = ""
    for code in watched_codes:
        pavilion_name = data_manager.get_pavilion_name(code)
        watched_list_text += f"• *{pavilion_name}* (`{code}`)\n"

    if watched_list_text:
        message_blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": watched_list_text}}
        )

    respond(
        blocks=message_blocks,
        response_type="in_channel",
        # thread_ts=command["event"]["ts"], # Removed for slash commands
    )


@app.command("/set_ticket_ids")
def set_user_ticket_ids(ack, respond, command):
    """
    Allows a user to set their personal ticket IDs for booking links.
    IDs should be comma-separated.
    """
    ack()
    user_id = command["user_id"]
    ids_string = command["text"].strip()

    if not ids_string:
        watched_pavilion_manager.set_user_ticket_ids(user_id, [])
        respond(
            text="Your ticket IDs have been cleared. To set new IDs, use `/set_ticket_ids [ID1,ID2,...]` 🎫",
            response_type="ephemeral",
            # thread_ts=command["event"]["ts"], # Removed for slash commands
        )
        return

    # Split by comma and clean up whitespace
    ids_list = [id.strip() for id in ids_string.split(",") if id.strip()]

    if not ids_list:
        respond(
            text="No valid IDs found. Please provide comma-separated IDs. Example: `/set_ticket_ids 12345,67890` 🧐",
            response_type="ephemeral",
            # thread_ts=command["event"]["ts"], # Removed for slash commands
        )
        return

    watched_pavilion_manager.set_user_ticket_ids(user_id, ids_list)
    respond(
        text=f"Your ticket IDs have been set to: `{', '.join(ids_list)}` ✅. This will be used for booking links.",
        response_type="ephemeral",
        # thread_ts=command["event"]["ts"], # Removed for slash commands
    )
    logging.info(f"User {user_id} set ticket IDs: {ids_list}")


@app.command("/show_status_expo")
def show_single_pavilion_status(ack, respond, command):
    """Shows the current status of a specified pavilion."""
    ack()
    user_id = command["user_id"]  # Get user ID to fetch their specific ticket IDs
    args = command["text"].strip().split()
    if not args:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text="Please specify a pavilion code to show its status. Example: `/show_status_expo HOH0` 🧐",
            response_type="ephemeral",
        )
        return

    code = args[0].upper()
    pavilion_name = data_manager.get_pavilion_name(code)
    pavilion_url = data_manager.get_pavilion_url(code)

    if (
        not pavilion_name or pavilion_name == code
    ):  # Check if it's a valid known pavilion
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"Pavilion with code `{code}` not found. Please check `/list_all_expo` for valid codes. ❌",
            response_type="ephemeral",
        )
        return

    schedules = data_manager.get_specific_pavilion_status(code)
    if not schedules:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"No availability information found for *{pavilion_name}* (`{code}`) at this moment. It might not have time-based availability. 🤷‍♂️",
            response_type="ephemeral",
        )
        return

    # Get user's specific ticket IDs for the link
    user_ticket_ids_for_link = watched_pavilion_manager.get_user_ticket_ids(user_id)
    current_expo_link = get_expo_ticket_link(
        pavilion_id=code, ids_list=user_ticket_ids_for_link
    )

    # Sort schedules by time
    sorted_schedules = sorted(schedules.items())

    # Prepare fields for availability status
    status_fields = []
    MAX_SLOTS_DISPLAY = 15  # Limit number of time slots to display directly as fields

    for i, (time_slot, status) in enumerate(sorted_schedules):
        if i >= MAX_SLOTS_DISPLAY:
            status_fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"_{len(sorted_schedules) - i} more time slots..._",
                }
            )
            break
        status_fields.append(
            {
                "type": "mrkdwn",
                "text": f"*Time {time_slot[:2]}:{time_slot[2:]}:* {get_status_text(status)}",
            }
        )

    message_blocks = [
        {
            "type": "header",  # Header block for the main title
            "text": {
                "type": "plain_text",
                "text": f"📊 Current Availability: {pavilion_name}",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    # Add booking link in a section
    message_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Booking Link:* <{current_expo_link}|Click to Book> 🎟️",
            },
        }
    )

    # Add original pavilion URL if different and available (optional, might remove if link above is sufficient)
    if pavilion_url and pavilion_url != current_expo_link:
        message_blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Original Pavilion Info: <{pavilion_url}|Link>",
                    }
                ],
            }
        )

    message_blocks.append({"type": "divider"})
    message_blocks.append({"type": "section", "fields": status_fields})

    message_blocks.append({"type": "divider"})
    message_blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Last updated: <!date^"
                    + str(int(time.time()))
                    + "^{date_num} {time_secs}|Fallback Time>",  # Dynamic timestamp
                }
            ],
        }
    )

    respond(
        blocks=message_blocks,
        response_type="in_channel",
        thread_ts=command["event"]["ts"],
    )


@app.command("/search_expo")
def search_pavilions(ack, respond, command):
    """
    Searches for pavilions by a partial name query and returns matching codes.
    """
    ack()
    query = command["text"].strip()

    if not query:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text="Please provide a search query. Example: `/search_expo Japan Pavilion` 🧐",
            response_type="ephemeral",
        )
        return

    search_results = data_manager.search_pavilions_by_name(query)

    if not search_results:
        respond(
            # thread_ts=command["event"]["ts"], # Removed for slash commands
            text=f"No pavilions found matching '{query}'. Please try a different query. 🤷‍♀️",
            response_type="ephemeral",
        )
        return

    message_blocks = [
        {
            "type": "header",  # Header block for search results
            "text": {
                "type": "plain_text",
                "text": f"🔍 Found {len(search_results)} pavilion(s) matching '{query}':",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    search_list_text = ""
    MAX_SEARCH_RESULTS_DISPLAY = 20
    for i, p in enumerate(search_results):
        if i >= MAX_SEARCH_RESULTS_DISPLAY:
            search_list_text += f"\n_... and {len(search_results) - i} more results. Please refine your search._ 💡"
            break
        search_list_text += f"• `{p['code']}`: {p['name']}\n"

    if search_list_text:
        message_blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": search_list_text}}
        )

    message_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Use `/watch_expo [CODE]` or `/show_status_expo [CODE]` with the code to get more details! ✨",
            },
        }
    )

    respond(
        blocks=message_blocks,
        response_type="in_channel",
        # thread_ts=command["event"]["ts"], # Removed for slash commands
    )


### Main execution block ###
if __name__ == "__main__":
    # Ensure the notification channel ID is set
    if not SLACK_EXPO_NOTIFICATION_CHANNEL_ID:
        logging.error(
            "SLACK_EXPO_NOTIFICATION_CHANNEL_ID environment variable is not set. Notifications will not be sent."
        )
        # Exit if essential for notifications
        exit(1)

    # Initial data load before starting monitors
    logging.info("Performing initial data load...")
    initial_data = fetch_data_json()
    if initial_data:
        data_manager.load_initial_data(initial_data)
    else:
        logging.error(
            "Failed to load initial data. Bot may not function correctly without it."
        )

    # Start data monitoring threads
    data_thread = threading.Thread(target=monitor_data_json, daemon=True)
    add_thread = threading.Thread(target=monitor_add_json, daemon=True)

    data_thread.start()
    add_thread.start()

    logging.info("Starting Slack SocketModeHandler...")
    # Start the Slack app
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
