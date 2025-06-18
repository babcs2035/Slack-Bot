import json
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# File to store watched pavilions
WATCHED_FILE = "watched_pavilions.json"
# File to store user-specific ticket IDs
USER_TICKET_IDS_FILE = "user_ticket_ids.json"


class WatchedPavilionManager:
    def __init__(self):
        # Stores codes of pavilions watched by users
        self.watched_codes = set()
        # Stores user-specific ticket IDs: {user_id: [id1, id2, ...], ...}
        self.user_ticket_ids = {}
        self._load_watched_pavilions()
        self._load_user_ticket_ids()

    def _load_watched_pavilions(self):
        """Loads watched pavilions from a JSON file."""
        if os.path.exists(WATCHED_FILE):
            try:
                with open(WATCHED_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.watched_codes = set(data)
                        logging.info(
                            f"Loaded {len(self.watched_codes)} watched pavilions from {WATCHED_FILE}"
                        )
                    else:
                        logging.warning(
                            f"Watched pavilions file {WATCHED_FILE} is not a list. Starting with empty set."
                        )
                        self.watched_codes = set()
            except json.JSONDecodeError as e:
                logging.error(
                    f"Error decoding {WATCHED_FILE}: {e}. Starting with empty set."
                )
                self.watched_codes = set()
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred loading {WATCHED_FILE}: {e}. Starting with empty set."
                )
                self.watched_codes = set()
        else:
            logging.info(
                f"Watched pavilions file {WATCHED_FILE} not found. Starting with empty set."
            )

    def _save_watched_pavilions(self):
        """Saves watched pavilions to a JSON file."""
        try:
            with open(WATCHED_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.watched_codes), f, indent=4, ensure_ascii=False)
            logging.info(
                f"Saved {len(self.watched_codes)} watched pavilions to {WATCHED_FILE}"
            )
        except IOError as e:
            logging.error(f"Error saving {WATCHED_FILE}: {e}")

    def _load_user_ticket_ids(self):
        """Loads user-specific ticket IDs from a JSON file."""
        if os.path.exists(USER_TICKET_IDS_FILE):
            try:
                with open(USER_TICKET_IDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.user_ticket_ids = data
                        logging.info(
                            f"Loaded {len(self.user_ticket_ids)} user ticket ID entries from {USER_TICKET_IDS_FILE}"
                        )
                    else:
                        logging.warning(
                            f"User ticket IDs file {USER_TICKET_IDS_FILE} is not a dict. Starting with empty dict."
                        )
                        self.user_ticket_ids = {}
            except json.JSONDecodeError as e:
                logging.error(
                    f"Error decoding {USER_TICKET_IDS_FILE}: {e}. Starting with empty dict."
                )
                self.user_ticket_ids = {}
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred loading {USER_TICKET_IDS_FILE}: {e}. Starting with empty dict."
                )
                self.user_ticket_ids = {}
        else:
            logging.info(
                f"User ticket IDs file {USER_TICKET_IDS_FILE} not found. Starting with empty dict."
            )

    def _save_user_ticket_ids(self):
        """Saves user-specific ticket IDs to a JSON file."""
        try:
            with open(USER_TICKET_IDS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.user_ticket_ids, f, indent=4, ensure_ascii=False)
            logging.info(
                f"Saved {len(self.user_ticket_ids)} user ticket ID entries to {USER_TICKET_IDS_FILE}"
            )
        except IOError as e:
            logging.error(f"Error saving {USER_TICKET_IDS_FILE}: {e}")

    def add_pavilion(self, code):
        """
        Adds a pavilion code to the watched list.
        Returns True if added, False if already present.
        """
        if code in self.watched_codes:
            return False
        self.watched_codes.add(code)
        self._save_watched_pavilions()
        return True

    def remove_pavilion(self, code):
        """
        Removes a pavilion code from the watched list.
        Returns True if removed, False if not present.
        """
        if code not in self.watched_codes:
            return False
        self.watched_codes.remove(code)
        self._save_watched_pavilions()
        return True

    def get_watched_list(self):
        """Returns the current list of watched pavilion codes."""
        return list(self.watched_codes)

    def set_user_ticket_ids(self, user_id, ids: list):
        """
        Sets ticket IDs for a specific user.
        Args:
            user_id (str): The Slack user ID.
            ids (list): A list of ticket IDs (strings).
        """
        self.user_ticket_ids[user_id] = [
            str(id).strip() for id in ids if str(id).strip()
        ]  # Ensure strings and non-empty
        self._save_user_ticket_ids()
        logging.info(
            f"Set ticket IDs for user {user_id}: {self.user_ticket_ids[user_id]}"
        )

    def get_user_ticket_ids(self, user_id):
        """
        Retrieves ticket IDs for a specific user.
        Returns a list of strings, or an empty list if not found.
        """
        return self.user_ticket_ids.get(user_id, [])


# Initialize watched pavilion manager
watched_pavilion_manager = WatchedPavilionManager()

if __name__ == "__main__":
    # Example usage:
    logging.info(f"Initial watched list: {watched_pavilion_manager.get_watched_list()}")

    watched_pavilion_manager.add_pavilion("HOH0")
    watched_pavilion_manager.add_pavilion("H1HF")
    logging.info(
        f"After adding HOH0, H1HF: {watched_pavilion_manager.get_watched_list()}"
    )

    watched_pavilion_manager.add_pavilion("HOH0")  # Should return False
    logging.info(
        f"After adding HOH0 again: {watched_pavilion_manager.get_watched_list()}"
    )

    watched_pavilion_manager.remove_pavilion("H1HF")
    logging.info(f"After removing H1HF: {watched_pavilion_manager.get_watched_list()}")

    watched_pavilion_manager.remove_pavilion("UNKNOWN_CODE")  # Should return False
    logging.info(
        f"After removing UNKNOWN_CODE: {watched_pavilion_manager.get_watched_list()}"
    )

    watched_pavilion_manager.add_pavilion("TEST1")
    watched_pavilion_manager.add_pavilion("TEST2")
    logging.info(f"Final watched list: {watched_pavilion_manager.get_watched_list()}")

    # Test user ticket IDs
    user_id = "U1234567890"
    watched_pavilion_manager.set_user_ticket_ids(user_id, ["ID_A", "ID_B"])
    logging.info(
        f"Ticket IDs for {user_id}: {watched_pavilion_manager.get_user_ticket_ids(user_id)}"
    )

    watched_pavilion_manager.set_user_ticket_ids(user_id, ["ID_C"])
    logging.info(
        f"Updated Ticket IDs for {user_id}: {watched_pavilion_manager.get_user_ticket_ids(user_id)}"
    )

    logging.info(
        f"Ticket IDs for unknown user: {watched_pavilion_manager.get_user_ticket_ids('UUNKNOWN')}"
    )
