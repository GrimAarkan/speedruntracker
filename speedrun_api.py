import requests
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Outlast Game ID
OUTLAST_GAME_ID = "76r43l18"  # Outlast original game ID

# Outlast Main Game Categories (Updated with Insane category)
OUTLAST_CATEGORIES = {
    "any%": {
        "id": "w20wryod",
        "name": "Any%",
        "main_game_variable": [
            {
                "id": "onv639m8",
                "value": "gq7nyep1"  # Main Game
            }
        ]
    },
    "all_chapters": {
        "id": "vdoor39d",
        "name": "All Chapters",
        "main_game_variable": [
            {
                "id": "wl36qj6l",
                "value": "jq648r71"
            }
        ]
    },
    "glitchless": {
        "id": "wkpo8v82",
        "name": "Glitchless",
        "main_game_variable": [
            {
                "id": "onvvxkwn",  # No S&Q
                "value": "4qyg584q"
            },
            {
                "id": "e8myk7x8",
                "value": "81052z5q"
            }
        ]
    },
    "no_oob": {
        "id": "mkezgrnk",
        "name": "No OOB",
        "main_game_variable": [
            {
                "id": "68kyoo3l",  # AC
                "value": "qvvvjw6q"
            },
            {
                "id": "rn11qypn",
                "value": "81p7rok1"
            }
        ]
    },
    "100%": {
        "id": "wk67xvpd",
        "name": "100%",
        "main_game_variable": [
            {
                "id": "2lgzpeo8",
                "value": "mlnygmd1"
            }
        ]
    },
    "insane": {
        "id": "zdn45xxk",
        "name": "Insane",
        "main_game_variable": [
            {
                "id": "2lgeojo8",  # Any% Insane
                "value": "lx5yv8g1"
            },
            {
                "id": "ylpv5ydl",  # Main Game
                "value": "z19406kl"
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
    hours = int(time_seconds // 3600)
    minutes = int((time_seconds % 3600) // 60)
    seconds = int(time_seconds % 60)
    milliseconds = int((time_seconds % 1) * 1000)
    
    # If hours is 0, only show minutes and seconds
    if hours == 0:
        formatted_time = f"{minutes:02d}:{seconds:02d}"
        detailed_time = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    else:
        formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        detailed_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
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
            runner_data = requests.get(f"https://www.speedrun.com/api/v1/users/{runner_id}").json()
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
    if "submitted" in run_data:
        submitted_date = datetime.fromisoformat(run_data["submitted"].replace("Z", "+00:00"))
        return submitted_date.strftime("%Y-%m-%d")
    else:
        return "Unknown date"

def get_category_record(category_key):
    """
    Get the world record for a specific Outlast category
    
    Args:
        category_key (str): The category key from OUTLAST_CATEGORIES
        
    Returns:
        dict: The record data or None if category not found
        
    Raises:
        Exception: If there's an error fetching the data
    """
    if category_key not in OUTLAST_CATEGORIES:
        logger.error(f"Unknown category key: {category_key}")
        return None
    
    category = OUTLAST_CATEGORIES[category_key]
    api_url = f"https://www.speedrun.com/api/v1/leaderboards/{OUTLAST_GAME_ID}/category/{category['id']}?top=1"
    
    # Add main_game_variable to the API URL if it's present
    for variable in category["main_game_variable"]:
        api_url += f"&var-{variable['id']}={variable['value']}"
    
    try:
        logger.debug(f"Fetching data from: {api_url}")
        response = requests.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract world record data
        wr_run = data["data"]["runs"][0]["run"]
        wr_time = wr_run["times"]["primary_t"]
        
        # Get runner information
        runner_name = get_runner_name(wr_run["players"][0])
        
        # Format time
        formatted_time, detailed_time = format_time(wr_time)
        
        # Get submission date
        date_string = get_submission_date(wr_run)
        
        return {
            "raw_time": wr_time,
            "formatted_time": formatted_time,
            "detailed_time": detailed_time,
            "runner": runner_name,
            "date": date_string,
            "game": "Outlast",
            "category": category["name"],
            "category_id": category["id"]
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Failed to connect to Speedrun.com API: {str(e)}")
    except (KeyError, IndexError) as e:
        logger.error(f"Data parsing error: {str(e)}")
        raise Exception(f"Failed to parse speedrun data: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise Exception(f"Unknown error: {str(e)}")

def get_outlast_wr():
    """
    Fetch the current world record for Outlast Any% category.
    
    Returns:
        dict: A dictionary containing the world record data
    
    Raises:
        Exception: If there's an error fetching the world record data
    """
    return get_category_record("any%")

def get_all_categories():
    """
    Fetch world records for all main game categories
    
    Returns:
        dict: Dictionary with category keys and their record data
    """
    results = {}
    for category_key in OUTLAST_CATEGORIES:
        try:
            results[category_key] = get_category_record(category_key)
        except Exception as e:
            logger.error(f"Error fetching {category_key} category: {str(e)}")
            results[category_key] = None
    
    return results
