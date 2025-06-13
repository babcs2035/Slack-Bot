import json
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# File to store watched pavilions
WATCHED_FILE = "watched_pavilions.json"


class WatchedPavilionManager:
    def __init__(self):
        # Stores codes of pavilions watched by users
        self.watched_codes = set()
        self._load_watched_pavilions()

    def _load_watched_pavilions(self):
        """Loads watched pavilions from a JSON file."""
        if os.path.exists(WATCHED_FILE):
            try:
                with open(WATCHED_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure loaded data is a list to convert to set
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
