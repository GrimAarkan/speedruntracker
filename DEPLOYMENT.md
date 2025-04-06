# Deploying Outlast Speedrun Tracker to Render

This guide will walk you through deploying the Outlast Speedrun Tracker application to Render.

## Prerequisites

1. A GitHub account
2. A Render account (sign up at [render.com](https://render.com))
3. Your GitHub Personal Access Token (for GitHub integration)

## Step 1: Ensure Your Project is Ready

Your project already has all the necessary files for deployment:

- `main.py` - Entry point for the application
- `app.py` - Flask application configuration
- `speedrun_api.py`, `whistleblower_api.py`, `outlast2_api.py` - API modules
- `templates/` directory with HTML templates
- `static/` directory with CSS and JavaScript files
- `render.yaml` - Render configuration file

## Step 2: Push Your Project to GitHub

If you haven't already, create a GitHub repository and push your project to it:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/outlast-speedrun-tracker.git
git push -u origin main
```

## Step 3: Deploy to Render

1. Log in to your Render account at [dashboard.render.com](https://dashboard.render.com)
2. Click the "New" button and select "Blueprint" 
3. Connect your GitHub account and select your repository
4. Render will automatically detect the `render.yaml` file
5. Review the settings and click "Apply"

## Step 4: Configure Environment Variables

After deployment, you need to set up the environment variables in the Render dashboard:

1. Navigate to your web service in the Render dashboard
2. Go to the "Environment" tab
3. Add the following environment variables:
   - `GITHUB_TOKEN`: Your GitHub Personal Access Token
   - `GITHUB_REPO_OWNER`: Your GitHub username
   - `GITHUB_REPO_NAME`: The repository name for storing record data

## Step 5: Verify Deployment

1. After deployment completes, click on the URL provided by Render
2. Verify that your application is working correctly
3. Test the record retrieval functionality
4. Test the export functionality

## Troubleshooting

If you encounter issues:

1. Check the Render logs for error messages
2. Verify that all environment variables are set correctly
3. Ensure your GitHub token has the correct permissions

## Automatic Deployments

Render will automatically redeploy your application whenever you push changes to your GitHub repository.

## Build and Start Commands

The following commands are configured in `render.yaml`:

- **Build Command**: `pip install -r requirements.txt`
  - Installs all Python dependencies required by the application

- **Start Command**: `gunicorn main:app --bind 0.0.0.0:$PORT`
  - Starts the Flask application using Gunicorn
  - Binds to the port assigned by Render ($PORT environment variable)