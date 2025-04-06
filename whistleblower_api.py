"""
API Module for fetching speedrun data for Outlast: Whistleblower DLC.
"""
import logging
import requests
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Game and category IDs
GAME_ID = "76r43l18"

# Category mapping
WHISTLEBLOWER_CATEGORIES = {
    "any": {
        "id":
        "w20wryod",
        "name":
        "Any%",
        "main_game_variable": [{
            "id": "onv639m8",
            "value": "21gjkr61"  # Main Game
        }]
    },
    "all_chapters": {
        "id": "vdoor39d",
        "name": "All Chapters",
        "main_game_variable": [{
            "id": "wl36qj6l",
            "value": "5lmx7641"
        }]
    },
    "glitchless": {
        "id":
        "wkpo8v82",
        "name":
        "Glitchless",
        "main_game_variable": [
            {
                "id": "onvvxkwn",  # No S&Q
                "value": "4qyg584q"
            },
            {
                "id": "e8myk7x8",
                "value": "5lmx7k41"
            }
        ]
    },
    "no_oob": {
        "id":
        "mkezgrnk",
        "name":
        "No OOB",
        "main_game_variable": [
            {
                "id": "68kyoo3l",  # AC
                "value": "qvvvjw6q"
            },
            {
                "id": "rn11qypn",
                "value": "xqkrp0y1"
            }
        ]
    },
    "100": {
        "id": "wk67xvpd",
        "name": "100%",
        "main_game_variable": [{
            "id": "2lgzpeo8",
            "value": "9qjzpng1"
        }]
    },
    "insane": {
        "id":
        "zdn45xxk",
        "name":
        "Insane",
        "main_game_variable": [
            {
                "id": "2lgeojo8",  # Any% Insane
                "value": "lx5yv8g1"
            },
            {
                "id": "ylpv5ydl",  # Main Game
                "value": "p125grk1"
            }
        ]
    }
}


def format_time(time_seconds):
    """
    Format time in seconds to HH:MM:SS and HH:MM:SS.ms formats
    
    Args:
        time_seconds (float): Time in seconds
        
    Returns:
        tuple: (formatted_time, detailed_time)
    """
    hours = int(time_seconds / 3600)
    minutes = int((time_seconds % 3600) / 60)
    seconds = int(time_seconds % 60)
    milliseconds = int((time_seconds - int(time_seconds)) * 1000)

    # If hours is 0, only show minutes and seconds
    if hours == 0:
        # Basic format (MM:SS)
        formatted_time = f"{minutes:02}:{seconds:02}"
        # Detailed format (MM:SS.ms)
        detailed_time = f"{minutes:02}:{seconds:02}.{milliseconds:03}"
    else:
        # Basic format (HH:MM:SS)
        formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
        # Detailed format (HH:MM:SS.ms)
        detailed_time = f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

    return formatted_time, detailed_time


def get_runner_name(player_data):
    """
    Get runner name from player data
    
    Args:
        player_data (dict): Player data from the API
    
    Returns:
        str: Runner name
    """
    runner_name = "Unknown"

    if "id" in player_data:
        try:
            runner_id = player_data["id"]
            runner_data = requests.get(
                f"https://www.speedrun.com/api/v1/users/{runner_id}").json()
            runner_name = runner_data["data"]["names"]["international"]
        except Exception as e:
            logger.error(f"Error fetching runner data: {str(e)}")

    return runner_name


def get_submission_date(run_data):
    """
    Get formatted submission date from run data
    
    Args:
        run_data (dict): Run data from the API
        
    Returns:
        str: Formatted date string
    """
    try:
        date_str = run_data.get("date", None)
        if date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%B %d, %Y")
        else:
            return "Unknown Date"
    except Exception as e:
        logger.error(f"Error formatting date: {str(e)}")
        return "Unknown Date"


def get_category_record(category_key):
    """
    Get the world record for a specific category in Outlast: Whistleblower
    
    Args:
        category_key (str): The category key from WHISTLEBLOWER_CATEGORIES
        
    Returns:
        dict: The record data or None if category not found
        
    Raises:
        Exception: If there's an error fetching the data
    """
    try:
        # Check if the category exists
        if category_key not in WHISTLEBLOWER_CATEGORIES:
            return None

        category_id = WHISTLEBLOWER_CATEGORIES[category_key]["id"]
        category_name = WHISTLEBLOWER_CATEGORIES[category_key]["name"]

        # URL for the leaderboard API
        base_url = f"https://www.speedrun.com/api/v1/leaderboards/{GAME_ID}/category/{category_id}?top=1"

        # Add variables if specified
        variables = WHISTLEBLOWER_CATEGORIES[category_key].get(
            "main_game_variable", [])
        variable_params = ""
        for var in variables:
            variable_params += f"&var-{var['id']}={var['value']}"

        url = base_url + variable_params

        # Log the URL being fetched
        logger.debug(f"Fetching data from: {url}")

        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract the run data
        runs = data.get("data", {}).get("runs", [])

        if not runs:
            return {
                "category": category_name,
                "formatted_time": "N/A",
                "detailed_time": "N/A",
                "raw_time": 0,
                "runner": "No runs yet",
                "date": "N/A",
                "category_key": category_key
            }

        run = runs[0]["run"]

        # Get the runner's info
        player_id = run["players"][0].get("id", None)
        player_data = None

        if player_id:
            player_url = f"https://www.speedrun.com/api/v1/users/{player_id}"
            player_response = requests.get(player_url)
            player_data = player_response.json().get("data", {})

        # Get the time
        time_seconds = run.get("times", {}).get("primary_t", 0)
        formatted_time, detailed_time = format_time(time_seconds)

        # Get the runner name
        runner = get_runner_name(
            player_data) if player_data else "Unknown Runner"

        # Get the submission date
        date = get_submission_date(run)

        # Return a dictionary with the world record info
        return {
            "category": category_name,
            "formatted_time": formatted_time,
            "detailed_time": detailed_time,
            "raw_time": time_seconds,
            "runner": runner,
            "date": date,
            "category_key": category_key
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        raise Exception(f"Failed to connect to speedrun.com API: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching category record: {str(e)}")
        raise Exception(f"Failed to fetch world record data: {str(e)}")


def get_all_categories():
    """
    Fetch world records for all categories of Outlast: Whistleblower
    
    Returns:
        dict: Dictionary with category keys and their record data
    """
    categories = {}

    # Get records for each category
    for key in WHISTLEBLOWER_CATEGORIES.keys():
        try:
            record = get_category_record(key)
            if record:
                categories[key] = record
            time.sleep(0.5)  # Add a small delay to avoid rate limiting
        except Exception as e:
            logger.error(f"Error fetching category {key}: {str(e)}")

    return categories
