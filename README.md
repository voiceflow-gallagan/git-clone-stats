# GitHub Repository Clone Statistics Tracker

A simple Python application for tracking and storing GitHub repository clone statistics. This tool fetches clone data from the GitHub API and maintains historical records in a SQLite database. It runs as an always on service and periodically fetches clone stats (total and unique) and displays them in an easy to use dashboard with shields.io badges available for use.

## Features

- Fetches repository clone statistics (total clones and unique cloners) from the GitHub API.
- Stores historical data in a SQLite database for robust and efficient querying.
- Avoids duplicate entries by only recording new data.
- Configurable for multiple repositories.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You will need to create a `requirements.txt` file containing `requests`)*

3.  **Set up your GitHub Personal Access Token and Username:**
    This script requires a GitHub Personal Access Token with the `repo` scope to access repository traffic data.

    Create a token in your [GitHub Developer settings](https://github.com/settings/tokens).

    Then, set the required environment variables:
    ```bash
    export GITHUB_TOKEN='your_github_personal_access_token'
    export GITHUB_USERNAME='your_github_username'
    ```

## Usage

### Fetching New Clone Data

To fetch the latest clone statistics from GitHub and update the database, simply run the script:

```bash
python app.py
```

The script will:
1.  Connect to the `github_stats.db` database file (or create it if it doesn't exist).
2.  Fetch clone statistics for the repositories defined in the `repos` list in `app.py`.
3.  Add any new daily clone records to the database.

You can run this script as frequently as you like; it will only add data for days not already present in the database.

### Retrieving Stored Data

You can query the `github_stats.db` SQLite database directly to retrieve historical data.

Here are some example queries you can run from your terminal:

**1. Open the database:**
```bash
sqlite3 github_stats.db
```

**2. View all records for a specific repository:**
```sql
SELECT * FROM clone_history WHERE repo = 'reclaimed';
```

**3. Get the total clone count for a repository:**
```sql
SELECT SUM(count) FROM clone_history WHERE repo = 'reclaimed';
```

**4. Get the total unique cloners for a repository:**
```sql
SELECT SUM(uniques) FROM clone_history WHERE repo = 'reclaimed';
```

**5. View all data, ordered by repository and date:**
```sql
SELECT * FROM clone_history ORDER BY repo, timestamp;
```

## Web Server & User Interface

This project includes a simple web server that provides a user interface for viewing repository statistics, a JSON API, and an automatic background synchronization feature.

### Running the Server

To start the server, run:
```bash
python server.py
```

The server will be available at `http://localhost:8000`.

### Automatic Background Sync

By default, the server will automatically sync with GitHub every 24 hours. You can configure the sync interval by setting the `SYNC_INTERVAL` environment variable before running the server.

Supported values are:
- `daily` (default)
- `weekly`
- `biweekly`

**Example:**
```bash
export SYNC_INTERVAL='weekly'
python server.py
```

### User Interface

Navigate to `http://localhost:8000` in your web browser to access the user interface. It displays a card for each repository with:
- The repository name
- A shields.io badge for total clones
- Total clone and unique cloner counts
- A button to copy the badge's Markdown code.

The interface also includes a "Sync with GitHub" button that triggers a fresh data pull from the GitHub API.

### API Endpoints

- **`GET /stats`**

  Returns a JSON array of all clone statistics from the database.

- **`GET /badge/<repo-name>`**

  Returns a shields.io badge displaying the total clone count for the specified repository.

  **Example:**
  `http://localhost:8000/badge/reclaimed` will redirect to:
  `https://img.shields.io/badge/clones-123-blue` (where 123 is the total clone count)

  **Example Response:**
  ```json
  [
      {
          "repo": "google_workspace_mcp",
          "timestamp": "2024-07-05T00:00:00Z",
          "count": 1,
          "uniques": 1
      },
      {
          "repo": "google_workspace_mcp",
          "timestamp": "2024-07-06T00:00:00Z",
          "count": 1,
          "uniques": 1
      }
  ]
  ```