import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DataManager:
    def __init__(self):
        # Stores the current status of all pavilions: {code: {name: str, url: str, schedules: {time: status, ...}}, ...}
        self.current_pavilion_data = {}
        # Stores only the status for comparison: {code: {time: status, ...}, ...}
        self.current_status_only = {}

    def load_initial_data(self, data_json):
        """
        Loads initial pavilion data from data.json.
        This should be called periodically (e.g., every minute) to ensure consistency.
        """
        if not data_json:
            logging.warning("No data_json provided for initial load.")
            return

        new_pavilion_data = {}
        new_status_only = {}

        for item in data_json:
            code = item.get("c")
            if not code:
                continue

            name = item.get("n", "Unknown Pavilion")
            url = item.get("u", "")
            schedules_list = item.get("s", [])

            schedules_dict = {
                s["t"]: s["s"] for s in schedules_list if "t" in s and "s" in s
            }

            new_pavilion_data[code] = {
                "name": name,
                "url": url,
                "schedules": schedules_dict,
            }
            new_status_only[code] = schedules_dict

        self.current_pavilion_data = new_pavilion_data
        self.current_status_only = new_status_only
        logging.info(
            f"Successfully loaded initial data for {len(self.current_pavilion_data)} pavilions."
        )

    def apply_updates(self, add_json):
        """
        Applies delta updates from add.json to the current data.
        Returns a dictionary of detected changes: {code: {time: (old_status, new_status)}, ...}
        """
        if not add_json:
            # logging.debug("No add_json provided for updates.") # Too verbose for 1-second interval
            return {}

        detected_changes = {}

        for code, updates in add_json.items():
            if code in self.current_pavilion_data:
                pavilion = self.current_pavilion_data[code]
                pavilion_status_only = self.current_status_only[code]

                for update in updates:
                    time = update.get("t")
                    new_status = update.get("s")

                    if time is not None and new_status is not None:
                        old_status = pavilion_status_only.get(time)

                        if old_status is None:
                            # New time slot added or first time seeing this slot
                            pavilion["schedules"][time] = new_status
                            pavilion_status_only[time] = new_status
                            # Consider this a change if it's new and has a status
                            if new_status is not None:
                                if code not in detected_changes:
                                    detected_changes[code] = {}
                                detected_changes[code][time] = (
                                    None,
                                    new_status,
                                )  # None for old_status indicates new slot
                                logging.debug(
                                    f"New time slot for {code} at {time}: {new_status}"
                                )
                        elif old_status != new_status:
                            # Status has changed
                            pavilion["schedules"][time] = new_status
                            pavilion_status_only[time] = new_status
                            if code not in detected_changes:
                                detected_changes[code] = {}
                            detected_changes[code][time] = (old_status, new_status)
                            logging.debug(
                                f"Status changed for {code} at {time}: {old_status} -> {new_status}"
                            )
            else:
                logging.debug(f"Received update for unknown pavilion code: {code}")

        return detected_changes

    def get_pavilion_name(self, code):
        """Returns the name of a pavilion given its code."""
        return self.current_pavilion_data.get(code, {}).get("name", code)

    def get_pavilion_url(self, code):
        """Returns the URL of a pavilion given its code."""
        return self.current_pavilion_data.get(code, {}).get("url", "")

    def get_all_pavilions_info(self):
        """Returns a list of all pavilions with their codes and names."""
        return [
            {"code": code, "name": data["name"]}
            for code, data in self.current_pavilion_data.items()
        ]

    def get_specific_pavilion_status(self, code):
        """Returns the current status of a specific pavilion."""
        return self.current_pavilion_data.get(code, {}).get("schedules", {})

    def search_pavilions_by_name(self, query):
        """
        Searches for pavilions whose names contain the given query string (case-insensitive).
        Returns a list of dictionaries: [{"code": code, "name": name}, ...].
        """
        if not query:
            return []

        matching_pavilions = []
        lower_query = query.lower()

        for code, data in self.current_pavilion_data.items():
            name = data.get("name", "")
            if lower_query in name.lower():
                matching_pavilions.append({"code": code, "name": name})

        # Sort results by name for consistency
        matching_pavilions.sort(key=lambda x: x["name"])
        return matching_pavilions


# Initialize data manager
data_manager = DataManager()

if __name__ == "__main__":
    # Example usage:
    from data_fetcher import fetch_data_json, fetch_add_json

    initial_data = fetch_data_json()
    data_manager.load_initial_data(initial_data)

    # Simulate an update
    sample_add_data = {
        "HOH0": [{"t": "1040", "s": 1}],
        "UNKNOWN_CODE": [{"t": "1200", "s": 2}],  # Test unknown code
    }
    changes = data_manager.apply_updates(sample_add_data)
    logging.info(f"Detected changes after update: {changes}")

    sample_add_data_2 = {
        "HOH0": [
            {"t": "1040", "s": 0},
            {"t": "1100", "s": 1},
        ],  # Change existing, add new time slot
        "CFR0": [{"t": "1824", "s": 2}],  # No change for this slot
    }
    changes_2 = data_manager.apply_updates(sample_add_data_2)
    logging.info(f"Detected changes after second update: {changes_2}")

    # Check status
    logging.info(
        f"Current status for HOH0: {data_manager.get_specific_pavilion_status('HOH0')}"
    )
    logging.info(f"Name of HOH0: {data_manager.get_pavilion_name('HOH0')}")
    logging.info(f"All pavilions count: {len(data_manager.get_all_pavilions_info())}")

    # Add example for search function
    logging.info("\n--- Search examples ---")
    search_results_japan = data_manager.search_pavilions_by_name("日本館")
    logging.info(f"Search '日本館': {search_results_japan}")

    search_results_kurage = data_manager.search_pavilions_by_name("クラゲ")
    logging.info(f"Search 'クラゲ': {search_results_kurage}")

    search_results_empty = data_manager.search_pavilions_by_name("")
    logging.info(f"Search empty: {search_results_empty}")

    search_results_nomatch = data_manager.search_pavilions_by_name(
        "存在しないパビリオン"
    )
    logging.info(f"Search '存在しないパビリオン': {search_results_nomatch}")
