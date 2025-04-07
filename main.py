from app import app, start_auto_export_thread

if __name__ == "__main__":
    # Start the auto-export thread when the app starts
    start_auto_export_thread()
    
    # Run the Flask application
    app.run(host="0.0.0.0", port=5000, debug=True)
