# Google Cloud App Engine Deployment Guide

This guide provides step-by-step instructions for deploying the git-clone-stats application to Google App Engine.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- A Google Cloud project created and linked
- Billing enabled on your Google Cloud project

## Deployment Steps

### 1. Ensure Required Files Exist

The following files are required for deployment:

- `app.yaml` - App Engine configuration
- `main.py` - Entry point for App Engine
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project metadata

### 2. Configure app.yaml

Update the environment variables in `app.yaml`:

```yaml
env_variables:
  GITHUB_USERNAME: "your-actual-github-username"
  GITHUB_TOKEN: "your-actual-github-token"
  SYNC_INTERVAL: "daily"
```

### 3. Initialize App Engine (if not already done)

```bash
gcloud app create --region=us-central1
```

**Note**: This step is irreversible and the region cannot be changed later.

### 4. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
```

### 5. Deploy the Application

```bash
gcloud app deploy --quiet
```

## Expected Output

Upon successful deployment, you should see:

```
Deployed service [default] to [https://your-project-id.uc.r.appspot.com]
```

## Post-Deployment

- Access your application at the provided URL
- Stream logs with: `gcloud app logs tail -s default`
- Browse the app with: `gcloud app browse`

## Troubleshooting

### Common Issues

1. **App Engine not initialized**: Run `gcloud app create --region=us-central1`
2. **Cloud Build API not enabled**: Run `gcloud services enable cloudbuild.googleapis.com`
3. **Storage bucket access issues**: Usually resolves after enabling Cloud Build API

### Environment Variables

Make sure to update the `GITHUB_USERNAME` and `GITHUB_TOKEN` in `app.yaml` before deployment for the application to function properly.

## Configuration Details

The `app.yaml` file includes:
- Python 3.9 runtime
- Automatic scaling (1-2 instances)
- Environment variables for GitHub integration
- Entry point: `python main.py`

## Technical Notes

- The server automatically uses the `PORT` environment variable provided by App Engine
- `main.py` serves as the entry point that imports and runs the server module
- App Engine handles port binding and scaling automatically