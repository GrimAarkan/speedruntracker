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

# Configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API_URL = "https://api.github.com"
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "GrimAarkan")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "speedruntracker")

GITHUB_FILENAME = "outlast_world_records_latest.txt"
WHISTLEBLOWER_FILENAME = "outlast_whistleblower_records_latest.txt"
OUTLAST2_FILENAME = "outlast2_records_latest.txt"

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Core API Routes
@app.route("/")
def index():
    """Render the main page."""
    categories = [{"key": k, "name": v["name"]} for k, v in OUTLAST_CATEGORIES.items()]
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

# Export Functions
def save_records_to_txt():
    """Save all world records to a text file."""
    try:
        categories_data = get_all_categories()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_world_records_{timestamp}.txt"
        file_path = os.path.join(EXPORT_DIR, filename)

        valid_categories = {k: v for k, v in categories_data.items() if v is not None and v.get("raw_time", 0) > 1}

        with open(file_path, 'w') as f:
            f.write(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
            f.write(f"from: https://www.speedrun.com/outlast | ")

            for record in valid_categories.values():
                f.write(f"{record['category']} ")
                f.write(f": {record['detailed_time']} ")
                f.write(f"by: {record['runner']} ")
                f.write(" | ")

        app.config['LATEST_EXPORT'] = file_path
        logger.info(f"Auto-export completed: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error in auto-export: {str(e)}")
        return None



def save_whistleblower_records_to_txt():
    """Save all world records for Outlast: Whistleblower to a text file."""
    try:
        categories_data = get_whistleblower_categories()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_whistleblower_records_{timestamp}.txt"
        file_path = os.path.join(EXPORT_DIR, filename)

        valid_categories = {k: v for k, v in categories_data.items() if v is not None and v.get("raw_time", 0) > 1}

        with open(file_path, 'w') as f:
            f.write(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
            f.write(f"from: https://www.speedrun.com/outlast | ")

            for record in valid_categories.values():
                f.write(f"{record['category']} ")
                f.write(f": {record['detailed_time']} ")
                f.write(f"by: {record['runner']} ")
                f.write(" | ")

        app.config['LATEST_WHISTLEBLOWER_EXPORT'] = file_path
        logger.info(f"Whistleblower export completed: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error in Whistleblower export: {str(e)}")
        return None

def save_outlast2_records_to_txt():
    """Save all world records for Outlast 2 to a text file."""
    try:
        categories_data = get_outlast2_categories()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast2_records_{timestamp}.txt"
        file_path = os.path.join(EXPORT_DIR, filename)

        valid_categories = {k: v for k, v in categories_data.items() if v is not None and v.get("raw_time", 0) > 1}

        with open(file_path, 'w') as f:
            f.write(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
            f.write(f"from: https://www.speedrun.com/outlast2 | ")

            for record in valid_categories.values():
                f.write(f"{record['category']} ")
                f.write(f": {record['detailed_time']} ")
                f.write(f"by: {record['runner']} ")
                f.write(" | ")

        app.config['LATEST_OUTLAST2_EXPORT'] = file_path
        logger.info(f"Outlast 2 export completed: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error in Outlast 2 export: {str(e)}")
        return None

# GitHub Integration
def push_to_github(file_path, github_path):
    """Push a file to GitHub repository."""
    try:
        if not GITHUB_TOKEN:
            logger.error("GitHub token not found. Cannot push to GitHub.")
            return False

        with open(file_path, 'r') as f:
            content = f.read()

        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }

        url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{github_path}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            file_sha = response.json()['sha']
            data = {
                'message': f'Update speedrun records {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'content': base64.b64encode(content.encode()).decode(),
                'sha': file_sha
            }
        else:
            data = {
                'message': f'Add speedrun records {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'content': base64.b64encode(content.encode()).decode()
            }

        response = requests.put(url, json=data, headers=headers)

        if response.status_code in (200, 201):
            logger.info(f"Successfully pushed {file_path} to GitHub")
            return True
        else:
            logger.error(f"Failed to push to GitHub. Status: {response.status_code}. Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error pushing to GitHub: {str(e)}")
        return False

# Auto-Export Functions
def auto_export_records():
    """Automatically export records at regular intervals."""
    logger.info("Auto-export thread starting - will run every 24 hours")
    while True:
        try:
            logger.info("Auto-export cycle beginning")
            txt_path = save_records_to_txt()

            if GITHUB_TOKEN and txt_path:
                try:
                    push_to_github(txt_path, GITHUB_FILENAME)
                    logger.info(f"Auto-pushed Outlast records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_FILENAME}")
                except Exception as github_error:
                    logger.error(f"Error pushing Outlast records to GitHub during auto-export: {str(github_error)}")

            try:
                whistleblower_path = save_whistleblower_records_to_txt()
                if GITHUB_TOKEN and whistleblower_path:
                    push_to_github(whistleblower_path, WHISTLEBLOWER_FILENAME)
                    logger.info(f"Auto-pushed Whistleblower records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{WHISTLEBLOWER_FILENAME}")
            except Exception as whistleblower_error:
                logger.error(f"Error exporting/pushing Whistleblower records: {str(whistleblower_error)}")

            try:
                outlast2_path = save_outlast2_records_to_txt()
                if GITHUB_TOKEN and outlast2_path:
                    push_to_github(outlast2_path, OUTLAST2_FILENAME)
                    logger.info(f"Auto-pushed Outlast 2 records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{OUTLAST2_FILENAME}")
            except Exception as outlast2_error:
                logger.error(f"Error exporting/pushing Outlast 2 records: {str(outlast2_error)}")

            cleanup_old_exports()
            time.sleep(21600)
        except Exception as e:
            logger.error(f"Error in auto-export thread: {str(e)}")
            time.sleep(7200)

def start_auto_export_thread():
    """Start the background thread for auto-exporting records."""
    auto_export_thread = threading.Thread(target=auto_export_records, daemon=True)
    auto_export_thread.start()
    logger.info("Auto-export thread started with 24-hour interval")

def cleanup_old_exports():
    """Remove old export files, keeping only the most recent ones."""
    try:
        txt_files = [f for f in os.listdir(EXPORT_DIR) if f.endswith('.txt')]
        txt_files.sort(key=lambda f: os.path.getmtime(os.path.join(EXPORT_DIR, f)), reverse=True)

        for old_file in txt_files[10:]:
            os.remove(os.path.join(EXPORT_DIR, old_file))
            logger.info(f"Cleaned up old export: {old_file}")
    except Exception as e:
        logger.error(f"Error cleaning up old exports: {str(e)}")

# Export Routes
@app.route("/exports")
def list_exports():
    """Display a list of all available exports."""
    try:
        txt_files = [f for f in os.listdir(EXPORT_DIR) if f.endswith('.txt')]

        txt_files.sort(key=lambda f: os.path.getmtime(os.path.join(EXPORT_DIR, f)), reverse=True)


        txt_exports = []
        for filename in txt_files:
            file_path = os.path.join(EXPORT_DIR, filename)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            size_kb = os.path.getsize(file_path) / 1024
            txt_exports.append({
                'filename': filename,
                'path': f"/exports/download/{filename}",
                'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                'size': f"{size_kb:.1f} KB"
            })


        return render_template("exports.html",
                           txt_exports=txt_exports,
                           repo_owner=GITHUB_REPO_OWNER,
                           repo_name=GITHUB_REPO_NAME)
    except Exception as e:
        logger.error(f"Error listing exports: {str(e)}")
        return render_template("error.html", error="Failed to list exports"), 500

@app.route("/export/outlast/records")
def export_records():
    """Export all world records to a text file and provide download link."""
    try:
        categories_data = get_all_categories()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outlast_world_records_{timestamp}.txt"
        file_path = os.path.join(EXPORT_DIR, filename)

        valid_categories = {k: v for k, v in categories_data.items() if v is not None and v.get("raw_time", 0) > 1}
        sorted_categories = sorted(valid_categories.values(), key=lambda x: x.get("raw_time", float('inf')))

        with open(file_path, 'w') as f:
            f.write(f"Outlast Speedrun World Records\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Data source: https://www.speedrun.com/outlast\n")
            f.write("-" * 60 + "\n\n")

            for record in sorted_categories:
                f.write(f"Category: {record['category']}\n")
                f.write(f"Time: {record['detailed_time']}\n")
                f.write(f"Runner: {record['runner']}\n")
                f.write(f"Date: {record['date']}\n")
                f.write("\n")

        app.config['LATEST_EXPORT'] = file_path
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Error exporting records: {str(e)}")
        return render_template("error.html", error="Failed to export records"), 500



@app.route("/latest/outlast/records")
def get_latest_records():
    """Return the latest exported records file if available."""
    try:
        file_path = app.config.get('LATEST_EXPORT')
        if file_path and os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return export_records()
    except Exception as e:
        logger.error(f"Error retrieving latest export: {str(e)}")
        return render_template("error.html", error="Failed to retrieve latest export"), 500

@app.route("/exports/download/<filename>")
def download_export(filename):
    """Download a specific export file."""
    try:
        file_path = os.path.join(EXPORT_DIR, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return render_template("error.html", error="Export file not found"), 404
    except Exception as e:
        logger.error(f"Error downloading export: {str(e)}")
        return render_template("error.html", error="Failed to download export"), 500

@app.route("/export/now")
def trigger_export():
    """Trigger an immediate export of the records."""
    try:
        txt_path = save_records_to_txt()
        whistleblower_path = save_whistleblower_records_to_txt()
        outlast2_path = save_outlast2_records_to_txt()

        if txt_path and whistleblower_path and outlast2_path:
            return redirect(url_for('list_exports'))
        else:
            flash("Failed to generate some exports", "danger")
            return redirect(url_for('list_exports'))
    except Exception as e:
        logger.error(f"Error triggering export: {str(e)}")
        flash("Error occurred while exporting", "danger")
        return redirect(url_for('list_exports'))

@app.route("/export/to-github")
def export_to_github():
    """Export the current records to GitHub."""
    try:
        txt_path = save_records_to_txt()

        if not txt_path:
            flash("Failed to generate export file", "danger")
            return redirect(url_for('list_exports'))

        success = push_to_github(txt_path, GITHUB_FILENAME)

        if success:
            flash(f"Successfully pushed records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_FILENAME}", "success")
        else:
            flash("Failed to push to GitHub. Check server logs for details.", "danger")

        return redirect(url_for('list_exports'))
    except Exception as e:
        logger.error(f"Error exporting to GitHub: {str(e)}")
        flash(f"Error exporting to GitHub: {str(e)}", "danger")
        return redirect(url_for('list_exports'))

@app.route("/export/whistleblower/to-github")
def export_whistleblower_to_github():
    """Export the Outlast: Whistleblower records to GitHub."""
    try:
        txt_path = save_whistleblower_records_to_txt()

        if not txt_path:
            flash("Failed to generate Whistleblower export file", "danger")
            return redirect(url_for('list_exports'))

        success = push_to_github(txt_path, WHISTLEBLOWER_FILENAME)

        if success:
            flash(f"Successfully pushed Whistleblower records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{WHISTLEBLOWER_FILENAME}", "success")
        else:
            flash("Failed to push Whistleblower records to GitHub. Check server logs for details.", "danger")

        return redirect(url_for('list_exports'))
    except Exception as e:
        logger.error(f"Error exporting Whistleblower to GitHub: {str(e)}")
        flash(f"Error exporting Whistleblower to GitHub: {str(e)}", "danger")
        return redirect(url_for('list_exports'))

@app.route("/export/outlast2/to-github")
def export_outlast2_to_github():
    """Export the Outlast 2 records to GitHub."""
    try:
        txt_path = save_outlast2_records_to_txt()

        if not txt_path:
            flash("Failed to generate Outlast 2 export file", "danger")
            return redirect(url_for('list_exports'))

        success = push_to_github(txt_path, OUTLAST2_FILENAME)

        if success:
            flash(f"Successfully pushed Outlast 2 records to GitHub: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{OUTLAST2_FILENAME}", "success")
        else:
            flash("Failed to push Outlast 2 records to GitHub. Check server logs for details.", "danger")

        return redirect(url_for('list_exports'))
    except Exception as e:
        logger.error(f"Error exporting Outlast 2 to GitHub: {str(e)}")
        flash(f"Error exporting Outlast 2 to GitHub: {str(e)}", "danger")
        return redirect(url_for('list_exports'))

@app.route("/api/cron/export-to-github", methods=["GET", "POST"])
def cron_export_to_github():
    """Special endpoint for Render Cron Jobs to trigger GitHub exports."""
    try:
        results = {"success": True, "results": []}

        try:
            txt_path = save_records_to_txt()
            if txt_path and GITHUB_TOKEN:
                success = push_to_github(txt_path, GITHUB_FILENAME)
                results["results"].append({"game": "Outlast", "success": success})
                logger.info(f"Cron job: Pushed Outlast records to GitHub: {success}")
        except Exception as e:
            logger.error(f"Cron job: Error exporting Outlast to GitHub: {str(e)}")
            results["results"].append({"game": "Outlast", "success": False, "error": str(e)})

        try:
            whistleblower_path = save_whistleblower_records_to_txt()
            if whistleblower_path and GITHUB_TOKEN:
                success = push_to_github(whistleblower_path, WHISTLEBLOWER_FILENAME)
                results["results"].append({"game": "Whistleblower", "success": success})
                logger.info(f"Cron job: Pushed Whistleblower records to GitHub: {success}")
        except Exception as e:
            logger.error(f"Cron job: Error exporting Whistleblower to GitHub: {str(e)}")
            results["results"].append({"game": "Whistleblower", "success": False, "error": str(e)})

        try:
            outlast2_path = save_outlast2_records_to_txt()
            if outlast2_path and GITHUB_TOKEN:
                success = push_to_github(outlast2_path, OUTLAST2_FILENAME)
                results["results"].append({"game": "Outlast 2", "success": success})
                logger.info(f"Cron job: Pushed Outlast 2 records to GitHub: {success}")
        except Exception as e:
            logger.error(f"Cron job: Error exporting Outlast 2 to GitHub: {str(e)}")
            results["results"].append({"game": "Outlast 2", "success": False, "error": str(e)})

        cleanup_old_exports()
        return jsonify(results)

    except Exception as e:
        logger.error(f"Cron job: Error in GitHub export endpoint: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template("error.html", error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template("error.html", error="Server error occurred"), 500