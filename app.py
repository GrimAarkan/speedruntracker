import os
import logging
import json
import threading
import time
import base64
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_file, flash, redirect, url_for

from speedrun_api import get_outlast_wr, get_category_record, get_all_categories, OUTLAST_CATEGORIES
from whistleblower_api import get_all_categories as get_whistleblower_categories, WHISTLEBLOWER_CATEGORIES
from outlast2_api import get_all_categories as get_outlast2_categories, OUTLAST2_CATEGORIES

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Directory for exports
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# GitHub API configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # Get token from environment variable
GITHUB_API_URL = "https://api.github.com"
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "GrimAarkan")  # Get from environment or use default
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "speedruntracker")  # Get from environment or use default

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Use consistent filename for GitHub updates
GITHUB_FILENAME = "outlast_world_records_latest.txt"  # Filename to update in GitHub
WHISTLEBLOWER_FILENAME = "outlast_whistleblower_records_latest.txt"  # Filename for Whistleblower updates
OUTLAST2_FILENAME = "outlast2_records_latest.txt"  # Filename for Outlast 2 updates


# Function to save data to a text file
def save_records_to_txt():
    """Save all world records to a text file."""
    try:
        # Get all categories data
        categories_data = get_all_categories()

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_world_records_{timestamp}.txt"
        file_path = os.path.join(EXPORT_DIR, filename)

        # Filter out any categories with invalid data
        valid_categories = {
            k: v
            for k, v in categories_data.items()
            if v is not None and v.get("raw_time", 0) > 1
        }

        # Write data to file
        with open(file_path, 'w') as f:
            f.write(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
            f.write(f"from: https://www.speedrun.com/outlast ")

            for record in valid_categories.values():
                f.write(f"{record['category']} ")
                f.write(f": {record['detailed_time']} ")
                f.write(f"by: {record['runner']} ")
                f.write(" | ")

        # Save the most recent file path for easy access
        app.config['LATEST_EXPORT'] = file_path
        logger.info(f"Auto-export completed: {file_path}")

        return file_path
    except Exception as e:
        logger.error(f"Error in auto-export: {str(e)}")
        return None


# Function to save data to a JSON file
def save_records_to_json():
    """Save all world records to a JSON file."""
    try:
        # Get all categories data
        categories_data = get_all_categories()

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_world_records_{timestamp}.json"
        file_path = os.path.join(EXPORT_DIR, filename)

        # Filter out any categories with invalid data
        valid_categories = {
            k: v
            for k, v in categories_data.items()
            if v is not None and v.get("raw_time", 0) > 1
        }

        # Create a structure with metadata
        export_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "source": "https://www.speedrun.com/outlast",
                "app_version": "1.0.0"
            },
            "records": valid_categories
        }

        # Write data to file
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Auto-export JSON completed: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error in auto-export JSON: {str(e)}")
        return None


# Function to auto-export records at regular intervals
def auto_export_records():
    """Automatically export records at regular intervals."""
    while True:
        try:
            # Export to local files
            txt_path = save_records_to_txt()
            save_records_to_json()

            # Push to GitHub if token is available
            if GITHUB_TOKEN and txt_path:
                try:
                    push_to_github(txt_path, GITHUB_FILENAME)
                    logger.info(
                        f"Auto-pushed records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_FILENAME}"
                    )
                except Exception as github_error:
                    logger.error(
                        f"Error pushing to GitHub during auto-export: {str(github_error)}"
                    )

            # Clean up old exports (keep only the last 10)
            cleanup_old_exports()

            # Sleep for 6 hours (21600 seconds) before next export
            time.sleep(21600)
        except Exception as e:
            logger.error(f"Error in auto-export thread: {str(e)}")
            # Sleep for 1 hour and try again
            time.sleep(3600)


# Function to clean up old export files
def cleanup_old_exports():
    """Remove old export files, keeping only the most recent ones."""
    try:
        # Get all text and JSON files in the export directory
        txt_files = [f for f in os.listdir(EXPORT_DIR) if f.endswith('.txt')]
        json_files = [f for f in os.listdir(EXPORT_DIR) if f.endswith('.json')]

        # Sort by modification time (newest first)
        txt_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(EXPORT_DIR, f)),
            reverse=True)
        json_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(EXPORT_DIR, f)),
            reverse=True)

        # Keep only the 10 most recent files of each type
        for old_file in txt_files[10:]:
            os.remove(os.path.join(EXPORT_DIR, old_file))
            logger.info(f"Cleaned up old export: {old_file}")

        for old_file in json_files[10:]:
            os.remove(os.path.join(EXPORT_DIR, old_file))
            logger.info(f"Cleaned up old export: {old_file}")
    except Exception as e:
        logger.error(f"Error cleaning up old exports: {str(e)}")


# Function to push a file to GitHub
def push_to_github(file_path, github_path):
    """
    Push a file to GitHub repository
    
    Args:
        file_path (str): Path to the local file to be uploaded
        github_path (str): Path in the GitHub repository
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not GITHUB_TOKEN:
            logger.error("GitHub token not found. Cannot push to GitHub.")
            return False

        # Read the file content
        with open(file_path, 'r') as f:
            content = f.read()

        # Get the current file to get the SHA (needed for update)
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # Check if the file exists
        url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{github_path}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            # File exists, get the SHA
            file_sha = response.json()['sha']

            # Update the file
            data = {
                'message':
                f'Update speedrun records {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'content': base64.b64encode(content.encode()).decode(),
                'sha': file_sha
            }
        else:
            # File doesn't exist, create it
            data = {
                'message':
                f'Add speedrun records {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'content': base64.b64encode(content.encode()).decode()
            }

        # Make the API request
        response = requests.put(url, json=data, headers=headers)

        if response.status_code in (200, 201):
            logger.info(f"Successfully pushed {file_path} to GitHub")
            return True
        else:
            logger.error(
                f"Failed to push to GitHub. Status: {response.status_code}. Response: {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"Error pushing to GitHub: {str(e)}")
        return False


# Start the auto-export thread when the app starts
auto_export_thread = threading.Thread(target=auto_export_records, daemon=True)
auto_export_thread.start()


@app.route("/")
def index():
    """Render the main page."""
    # Pass the categories to the template
    categories = [{
        "key": k,
        "name": v["name"]
    } for k, v in OUTLAST_CATEGORIES.items()]
    return render_template("index.html", categories=categories)


@app.route("/api/outlastwr")
def outlast_wr_api():
    """API endpoint to get the Outlast Any% world record time."""
    try:
        time_data = get_outlast_wr()
        return jsonify(time_data)
    except Exception as e:
        logger.error(f"Error fetching WR: {str(e)}")
        return jsonify({"error": "Failed to fetch world record data"}), 500


@app.route("/api/outlast/category/<category_key>")
def category_record_api(category_key):
    """API endpoint to get the world record for a specific category."""
    try:
        record_data = get_category_record(category_key)
        if record_data is None:
            return jsonify({"error": "Category not found"}), 404
        return jsonify(record_data)
    except Exception as e:
        logger.error(f"Error fetching category record: {str(e)}")
        return jsonify({"error": "Failed to fetch category record"}), 500


@app.route("/api/outlast/categories")
def all_categories_api():
    """API endpoint to get world records for all categories."""
    try:
        categories_data = get_all_categories()
        return jsonify(categories_data)
    except Exception as e:
        logger.error(f"Error fetching all categories: {str(e)}")
        return jsonify({"error": "Failed to fetch category records"}), 500


@app.route("/twitch/outlast/wr")
def twitch_command():
    """
    API endpoint for Twitch chat command to display world records
    Returns a formatted string for StreamElements custom command
    """
    try:
        categories_data = get_all_categories()

        # Filter out any categories with invalid data (like the 0.001 time for No OoB)
        valid_categories = {
            k: v
            for k, v in categories_data.items()
            if v is not None and v.get("raw_time", 0) > 1
        }

        # Sort categories by time (fastest first)
        sorted_categories = sorted(
            valid_categories.values(),
            key=lambda x: x.get("raw_time", float('inf')))

        # Format the response for Twitch chat
        response = "Outlast WRs: "
        for record in sorted_categories:
            response += f"{record['category']}: {record['formatted_time']} by {record['runner']} ({record['date']}), "

        # Remove the trailing comma and space
        response = response.rstrip(", ")

        return response
    except Exception as e:
        logger.error(f"Error generating Twitch command: {str(e)}")
        return "Error fetching Outlast world records"


@app.route("/twitch/outlast/wr/short")
def twitch_command_short():
    """
    Shorter API endpoint for Twitch chat command to display world records
    Returns a more concise formatted string for StreamElements custom command
    """
    try:
        # Only get the most common categories to save space in chat
        key_categories = ["any", "all_chapters", "glitchless", "100"]
        records = []

        for key in key_categories:
            record = get_category_record(key)
            if record and record.get("raw_time", 0) > 1:
                records.append(record)

        # Format the response for Twitch chat
        response = "Outlast WRs: "
        for record in records:
            # Use shorter category names to save space
            cat_name = record['category']
            if cat_name == "Any%":
                cat_name = "Any"

            response += f"{cat_name}: {record['formatted_time']} ({record['runner']}), "

        # Remove the trailing comma and space
        response = response.rstrip(", ")

        return response
    except Exception as e:
        logger.error(f"Error generating short Twitch command: {str(e)}")
        return "Error fetching Outlast world records"


@app.route("/outlastwr")
def outlast_wr():
    """Endpoint to get just the Outlast Any% world record time as text."""
    try:
        time_data = get_outlast_wr()
        if time_data is None:
            return "Error: Category not found"
        return time_data["formatted_time"]
    except Exception as e:
        logger.error(f"Error fetching WR: {str(e)}")
        return "Error fetching WR"


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template("error.html", error="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template("error.html", error="Server error occurred"), 500


@app.route("/export/outlast/records")
def export_records():
    """Export all world records to a text file and provide download link."""
    try:
        # Get all categories data
        categories_data = get_all_categories()

        # Create a directory for exports if it doesn't exist
        export_dir = os.path.join(os.path.dirname(__file__), "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_world_records_{timestamp}.txt"
        file_path = os.path.join(export_dir, filename)

        # Filter out any categories with invalid data (like the 0.001 time for No OoB)
        valid_categories = {
            k: v
            for k, v in categories_data.items()
            if v is not None and v.get("raw_time", 0) > 1
        }

        # Sort categories by time (fastest first)
        sorted_categories = sorted(
            valid_categories.values(),
            key=lambda x: x.get("raw_time", float('inf')))

        # Write data to file
        with open(file_path, 'w') as f:
            f.write(f"Outlast Speedrun World Records\n")
            f.write(
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"Data source: https://www.speedrun.com/outlast\n")
            f.write("-" * 60 + "\n\n")

            for record in sorted_categories:
                f.write(f"Category: {record['category']}\n")
                f.write(f"Time: {record['detailed_time']}\n")
                f.write(f"Runner: {record['runner']}\n")
                f.write(f"Date: {record['date']}\n")
                f.write("\n")

        # Save the most recent file path for easy access
        app.config['LATEST_EXPORT'] = file_path

        # Return the file as a download
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Error exporting records: {str(e)}")
        return render_template("error.html",
                               error="Failed to export records"), 500


@app.route("/export/outlast/records/json")
def export_records_json():
    """Export all world records to a JSON file and provide download link."""
    try:
        # Get all categories data
        categories_data = get_all_categories()

        # Create a directory for exports if it doesn't exist
        export_dir = os.path.join(os.path.dirname(__file__), "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_world_records_{timestamp}.json"
        file_path = os.path.join(export_dir, filename)

        # Filter out any categories with invalid data
        valid_categories = {
            k: v
            for k, v in categories_data.items()
            if v is not None and v.get("raw_time", 0) > 1
        }

        # Create a structure with metadata
        export_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "source": "https://www.speedrun.com/outlast",
                "app_version": "1.0.0"
            },
            "records": valid_categories
        }

        # Write data to file
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        # Return the file as a download
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Error exporting records as JSON: {str(e)}")
        return render_template("error.html",
                               error="Failed to export records as JSON"), 500


@app.route("/latest/outlast/records")
def get_latest_records():
    """Return the latest exported records file if available."""
    try:
        file_path = app.config.get('LATEST_EXPORT')
        if file_path and os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            # If no export exists, create one
            return export_records()
    except Exception as e:
        logger.error(f"Error retrieving latest export: {str(e)}")
        return render_template("error.html",
                               error="Failed to retrieve latest export"), 500


@app.route("/exports")
def list_exports():
    """Display a list of all available exports."""
    try:
        # Get all export files
        txt_files = [f for f in os.listdir(EXPORT_DIR) if f.endswith('.txt')]
        json_files = [f for f in os.listdir(EXPORT_DIR) if f.endswith('.json')]

        # Sort by modification time (newest first)
        txt_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(EXPORT_DIR, f)),
            reverse=True)
        json_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(EXPORT_DIR, f)),
            reverse=True)

        # Format the file data for display
        txt_exports = []
        for filename in txt_files:
            file_path = os.path.join(EXPORT_DIR, filename)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            size_kb = os.path.getsize(file_path) / 1024
            txt_exports.append({
                'filename':
                filename,
                'path':
                f"/exports/download/{filename}",
                'modified':
                mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                'size':
                f"{size_kb:.1f} KB"
            })

        json_exports = []
        for filename in json_files:
            file_path = os.path.join(EXPORT_DIR, filename)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            size_kb = os.path.getsize(file_path) / 1024
            json_exports.append({
                'filename':
                filename,
                'path':
                f"/exports/download/{filename}",
                'modified':
                mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                'size':
                f"{size_kb:.1f} KB"
            })

        return render_template("exports.html",
                               txt_exports=txt_exports,
                               json_exports=json_exports,
                               repo_owner=GITHUB_REPO_OWNER,
                               repo_name=GITHUB_REPO_NAME)
    except Exception as e:
        logger.error(f"Error listing exports: {str(e)}")
        return render_template("error.html",
                               error="Failed to list exports"), 500


@app.route("/exports/download/<filename>")
def download_export(filename):
    """Download a specific export file."""
    try:
        file_path = os.path.join(EXPORT_DIR, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return render_template("error.html",
                                   error="Export file not found"), 404
    except Exception as e:
        logger.error(f"Error downloading export: {str(e)}")
        return render_template("error.html",
                               error="Failed to download export"), 500


@app.route("/export/now")
def trigger_export():
    """Trigger an immediate export of the records."""
    try:
        txt_path = save_records_to_txt()
        json_path = save_records_to_json()

        if txt_path and json_path:
            return render_template("export_success.html",
                                   txt_file=os.path.basename(txt_path),
                                   json_file=os.path.basename(json_path))
        else:
            return render_template("error.html",
                                   error="Failed to generate exports"), 500
    except Exception as e:
        logger.error(f"Error triggering export: {str(e)}")
        return render_template("error.html",
                               error="Failed to trigger export"), 500


@app.route("/export/to-github")
def export_to_github():
    """Export the current records to GitHub."""
    try:
        # Create a new export
        txt_path = save_records_to_txt()

        if not txt_path:
            flash("Failed to generate export file", "danger")
            return redirect(url_for('list_exports'))

        # Push the file to GitHub
        success = push_to_github(txt_path, GITHUB_FILENAME)

        if success:
            flash(
                f"Successfully pushed records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_FILENAME}",
                "success")
        else:
            flash("Failed to push to GitHub. Check server logs for details.",
                  "danger")

        return redirect(url_for('list_exports'))
    except Exception as e:
        logger.error(f"Error exporting to GitHub: {str(e)}")
        flash(f"Error exporting to GitHub: {str(e)}", "danger")
        return redirect(url_for('list_exports'))


# Functions for second game
def save_whistleblower_records_to_txt():
    """Save all world records for Outlast: Whistleblower to a text file."""
    try:
        # Get all categories data
        categories_data = get_whistleblower_categories()

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_whistleblower_records_{timestamp}.txt"
        file_path = os.path.join(EXPORT_DIR, filename)

        # Filter out any categories with invalid data
        valid_categories = {
            k: v
            for k, v in categories_data.items()
            if v is not None and v.get("raw_time", 0) > 1
        }

        # Write data to file
        with open(file_path, 'w') as f:
            f.write(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
            f.write(f"from: https://www.speedrun.com/outlast ")

            for record in valid_categories.values():
                f.write(f"{record['category']} ")
                f.write(f": {record['detailed_time']} ")
                f.write(f"by: {record['runner']} ")
                f.write(" | ")

        # Save the most recent file path for easy access
        app.config['LATEST_WHISTLEBLOWER_EXPORT'] = file_path
        logger.info(f"Whistleblower export completed: {file_path}")

        return file_path
    except Exception as e:
        logger.error(f"Error in Whistleblower export: {str(e)}")
        return None


@app.route("/export/whistleblower/to-github")
def export_whistleblower_to_github():
    """Export the Outlast: Whistleblower records to GitHub."""
    try:
        # Create a new export
        txt_path = save_whistleblower_records_to_txt()

        if not txt_path:
            flash("Failed to generate Whistleblower export file", "danger")
            return redirect(url_for('list_exports'))

        # Push the file to GitHub
        success = push_to_github(txt_path, WHISTLEBLOWER_FILENAME)

        if success:
            flash(
                f"Successfully pushed Whistleblower records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{WHISTLEBLOWER_FILENAME}",
                "success")
        else:
            flash(
                "Failed to push Whistleblower records to GitHub. Check server logs for details.",
                "danger")

        return redirect(url_for('list_exports'))
    except Exception as e:
        logger.error(f"Error exporting Whistleblower to GitHub: {str(e)}")
        flash(f"Error exporting Whistleblower to GitHub: {str(e)}", "danger")
        return redirect(url_for('list_exports'))


# Functions for Outlast 2
def save_outlast2_records_to_txt():
    """Save all world records for Outlast 2 to a text file."""
    try:
        # Get all categories data
        categories_data = get_outlast2_categories()

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast2_records_{timestamp}.txt"
        file_path = os.path.join(EXPORT_DIR, filename)

        # Filter out any categories with invalid data
        valid_categories = {
            k: v
            for k, v in categories_data.items()
            if v is not None and v.get("raw_time", 0) > 1
        }

        # Write data to file
        with open(file_path, 'w') as f:
            f.write(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
            f.write(f"from: https://www.speedrun.com/outlast2 ")

            for record in valid_categories.values():
                f.write(f"{record['category']} ")
                f.write(f": {record['detailed_time']} ")
                f.write(f"by: {record['runner']} ")
                f.write(" | ")

        # Save the most recent file path for easy access
        app.config['LATEST_OUTLAST2_EXPORT'] = file_path
        logger.info(f"Outlast 2 export completed: {file_path}")

        return file_path
    except Exception as e:
        logger.error(f"Error in Outlast 2 export: {str(e)}")
        return None


@app.route("/export/outlast2/to-github")
def export_outlast2_to_github():
    """Export the Outlast 2 records to GitHub."""
    try:
        # Create a new export
        txt_path = save_outlast2_records_to_txt()

        if not txt_path:
            flash("Failed to generate Outlast 2 export file", "danger")
            return redirect(url_for('list_exports'))

        # Push the file to GitHub
        success = push_to_github(txt_path, OUTLAST2_FILENAME)

        if success:
            flash(
                f"Successfully pushed Outlast 2 records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{OUTLAST2_FILENAME}",
                "success")
        else:
            flash(
                "Failed to push Outlast 2 records to GitHub. Check server logs for details.",
                "danger")

        return redirect(url_for('list_exports'))
    except Exception as e:
        logger.error(f"Error exporting Outlast 2 to GitHub: {str(e)}")
        flash(f"Error exporting Outlast 2 to GitHub: {str(e)}", "danger")
        return redirect(url_for('list_exports'))
