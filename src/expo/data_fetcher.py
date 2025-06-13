import requests
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Base URL for the Expo API
BASE_URL = "https://expo.ebii.net/api"


def fetch_data_json():
    """
    Fetches the full data.json from the Expo API.
    Returns a list of pavilion data or None if an error occurs.
    """
    url = f"{BASE_URL}/data"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch data.json: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode data.json response: {e}")
        return None


def fetch_add_json():
    """
    Fetches the add.json (delta updates) from the Expo API.
    Returns a dictionary of updates or None if an error occurs.
    """
    url = f"{BASE_URL}/add"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch add.json: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode add.json response: {e}")
        return None


if __name__ == "__main__":
    # Example usage:
    data = fetch_data_json()
    if data:
        logging.info(f"Fetched data.json. First pavilion: {data[0]['n']}")

    add_data = fetch_add_json()
    if add_data:
        logging.info(f"Fetched add.json. Keys: {list(add_data.keys())}")
