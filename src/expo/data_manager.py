# data_manager.py

import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


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

            schedules_dict = {s["t"]: s["s"] for s in schedules_list if "t" in s and "s" in s}

            new_pavilion_data[code] = {
                "name": name,
                "url": url,
                "schedules": schedules_dict,
            }
            new_status_only[code] = schedules_dict

        self.current_pavilion_data = new_pavilion_data
        self.current_status_only = new_status_only
        logging.info(f"Successfully loaded initial data for {len(self.current_pavilion_data)} pavilions.")

    def apply_updates(self, add_json):
        """
        Applies delta updates from add.json to the current data.
        Returns a dictionary of detected changes: {code: {time: (old_status, new_status)}, ...}

        This method is optimized to detect *actual* changes in status compared to
        what is currently stored in self.current_status_only.
        """
        if not add_json:
            return {}

        detected_changes = {}

        for code, updates in add_json.items():
            # Ensure the pavilion exists in our current data before trying to update
            if code in self.current_pavilion_data:
                pavilion_schedules = self.current_pavilion_data[code]["schedules"]
                pavilion_status_only = self.current_status_only[code]

                for update in updates:
                    time_slot = update.get("t")
                    new_status = update.get("s")

                    if time_slot is not None and new_status is not None:
                        old_status = pavilion_status_only.get(time_slot)  # Get current known status

                        # Only proceed if the new status is different from the old one
                        if old_status != new_status:
                            # Update the stored status
                            pavilion_schedules[time_slot] = new_status
                            pavilion_status_only[time_slot] = new_status

                            # Record the change
                            if code not in detected_changes:
                                detected_changes[code] = {}
                            detected_changes[code][time_slot] = (old_status, new_status)
                            logging.debug(f"Status changed for {code} at {time_slot}: {old_status} -> {new_status}")
                        # else:
                        # If old_status == new_status, it's not a new change, so we do nothing.
                        # This is crucial for preventing duplicate notifications.
            # else:
            # This case is handled by data_manager, just log if needed
            # logging.debug(f"Received update for unknown pavilion code: {code}")

        return detected_changes

    def get_pavilion_name(self, code):
        """Returns the name of a pavilion given its code."""
        return self.current_pavilion_data.get(code, {}).get("name", code)

    def get_pavilion_url(self, code):
        """Returns the URL of a pavilion given its code."""
        return self.current_pavilion_data.get(code, {}).get("url", "")

    def get_all_pavilions_info(self):
        """Returns a list of all pavilions with their codes and names."""
        return [{"code": code, "name": data["name"]} for code, data in self.current_pavilion_data.items()]

    def get_specific_pavilion_status(self, code):
        """Returns the current status of a specific pavilion."""
        return self.current_pavilion_data.get(code, {}).get("schedules", {})


# Initialize data manager
data_manager = DataManager()

if __name__ == "__main__":
    initial_data = [
        {
            "c": "HOH0",
            "n": "Blue Ocean Dome",
            "u": "url_hoh0",
            "s": [{"t": "1040", "s": 2}],
        },
        {
            "c": "CFR0",
            "n": "Red Cross Pavilion",
            "u": "url_cfr0",
            "s": [{"t": "1824", "s": 0}],
        },
    ]
    data_manager.load_initial_data(initial_data)
    logging.info(f"Initial status for HOH0: {data_manager.get_specific_pavilion_status('HOH0')}")

    # Simulate an update where status changes (should notify)
    sample_add_data_change = {"HOH0": [{"t": "1040", "s": 1}]}  # Change from 2 to 1
    changes = data_manager.apply_updates(sample_add_data_change)
    logging.info(f"Detected changes (expected change): {changes}")  # Should show {'HOH0': {'1040': (2, 1)}}

    # Simulate an update where status is the same (should NOT notify)
    sample_add_data_no_change = {
        "HOH0": [{"t": "1040", "s": 1}]  # Still 1, no actual change
    }
    changes_no_notify = data_manager.apply_updates(sample_add_data_no_change)
    logging.info(f"Detected changes (expected no change): {changes_no_notify}")  # Should be {}

    # Simulate an update where status changes again
    sample_add_data_revert_change = {
        "HOH0": [{"t": "1040", "s": 2}]  # Change from 1 to 2
    }
    changes_revert = data_manager.apply_updates(sample_add_data_revert_change)
    logging.info(f"Detected changes (expected revert): {changes_revert}")  # Should show {'HOH0': {'1040': (1, 2)}}

    logging.info(f"Final status for HOH0: {data_manager.get_specific_pavilion_status('HOH0')}")
