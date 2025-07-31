<div align="center">

# git-stats - GitHub Repo Clone Stats & Analytics <img src="https://github.com/user-attachments/assets/dd25bc31-87e2-43ea-88de-e3de2222d066" width="80" align="right" />

[![PyPI](https://img.shields.io/pypi/v/git-clone-stats)](https://pypi.org/project/git-clone-stats/)
[![Python versions](https://img.shields.io/pypi/pyversions/git-clone-stats)](https://pypi.org/project/git-clone-stats/)
[![License](https://img.shields.io/github/license/taylorwilsdon/git-clone-stats)](LICENSE)

</div>

git-stats is the missing piece of GitHub analytics - even if you pay, they will only give you 14 days of history. Bizarre gap for a company built on data... 

But I digress. This repo is an agressively simple Python application for tracking and storing GitHub repository clone statistics. It has an extremely minimal HTML & JS frontend that requires no building, compiling or transpiling. 

The tool fetches clone data and view/traffic statistics from the GitHub API and maintains historical records in a SQLite or Firestore database. It runs as an always on service and periodically fetches clone stats (total and unique) plus view data and displays them in an easy to use dashboard with shields.io badges available for use.


<div align="center">
<video width=832 src="https://github.com/user-attachments/assets/c8704ac1-fd99-4bb7-8763-421eebc7c487"></video>
</div>

---

## Features

- **Complete GitHub Analytics**: Fetches repository clone statistics, view/traffic data (total views and unique viewers), and star counts from the GitHub API
- **Historical Data Storage**: Maintains unlimited historical records in SQLite (local) or Firestore (cloud) databases with robust querying capabilities
- **Smart Data Management**: Avoids duplicate entries by only recording new data points
- **Web Dashboard**: Modern, responsive UI with automatic background synchronization and dark/light theme support
- **Interactive Visualizations**: Time-series charts with customizable date ranges and repository filtering
- **Shields.io Badge Integration**: Generates embeddable badges for README files and documentation
- **Cloud-Ready Deployment**: One-command deployment to Google App Engine with auto-scaling and Firestore database support
- **Repository Management**: Add/remove tracked repositories through the web interface
- **Data Export/Import**: Backup and migration functionality for database portability
- **Flexible Sync Intervals**: Configurable automatic synchronization (daily, weekly, biweekly)
- **Modern CLI Interface**: Subcommands for sync and server operations with comprehensive help
- **PyPI-Ready Packaging**: Modern Python tooling support with uv compatibility for fast installation

### Quickstart with uv

Run directly without installation:

```bash
uv run git-clone-stats sync
uv run git-clone-stats server
```

## Installation

### From PyPI (recommended)

```bash
pip install git-clone-stats
```

### With uv (fastest)

```bash
uv tool install git-clone-stats
# or run directly without installing
uv run git-clone-stats --help
```

### From source

```bash
git clone https://github.com/taylorwilsdon/git-clone-stats.git
cd git-clone-stats
pip install -e .
```

### Docker (recommended for production)

Run git-stats in a production-ready Docker container:

```bash
# Using Docker Compose (easiest)
docker-compose up -d

# Or build and run manually
docker build -t git-stats .
docker run -d \
  -p 8080:8080 \
  -e GITHUB_TOKEN=your_token \
  -e GITHUB_USERNAME=your_username \
  -v $(pwd)/data:/app/data \
  git-stats
```

The Docker image includes:
- Multi-stage build for minimal size (~150MB)
- Non-root user execution for security
- Health checks for container orchestration
- Automatic restart on failure
- Volume mounting for persistent SQLite storage

## Configuration

Set up your GitHub Personal Access Token and Username. This requires a GitHub Personal Access Token with the `repo` scope to access repository traffic data.

1. Create a token in your [GitHub Developer settings](https://github.com/settings/tokens)
2. Set the required environment variables:

```bash
export GITHUB_TOKEN='your_github_personal_access_token'
export GITHUB_USERNAME='your_github_username'
```

## Usage

### Command Line Interface

The application provides a modern CLI with subcommands:

```bash
git-clone-stats --help
```

#### Sync clone data

To fetch the latest clone statistics from GitHub and update the database:

```bash
git-clone-stats sync
```

#### Start web server

To start the web dashboard server:

```bash
git-clone-stats server --port 8000
```

### Retrieving Stored Data

You can query the `github_stats.db` SQLite database directly to retrieve historical data.

Here are some example queries you can run from your terminal:

**1. Open the database:**
```bash
sqlite3 github_stats.db
```

**2. View all clone records for a specific repository:**
```sql
SELECT * FROM clone_history WHERE repo = 'reclaimed';
```

**3. View all view/traffic records for a specific repository:**
```sql
SELECT * FROM view_history WHERE repo = 'reclaimed';
```

**4. Get the total clone count for a repository:**
```sql
SELECT SUM(count) FROM clone_history WHERE repo = 'reclaimed';
```

**5. Get the total unique cloners for a repository:**
```sql
SELECT SUM(uniques) FROM clone_history WHERE repo = 'reclaimed';
```

**6. View all data, ordered by repository and date:**
```sql
SELECT * FROM clone_history ORDER BY repo, timestamp;
SELECT * FROM view_history ORDER BY repo, timestamp;
```

## Web Server & User Interface

The application includes a web server that provides a user interface for viewing repository statistics, a JSON API, and automatic background synchronization.

### Running the Server

To start the server:
```bash
git-clone-stats server --port 8000
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
git-clone-stats server
```

### User Interface

Navigate to `http://localhost:8000` in your web browser to access the user interface. The dashboard provides two viewing modes:

<div align="center">
<img width="70%" height="70%" alt="image" src="https://github.com/user-attachments/assets/f16b879d-f629-49a0-9fec-c17e827156b2" />
</div>

#### Card View (Default)
Displays a card for each repository with:
- The repository name and star count
- Total clone and unique cloner counts
- Collection date range (first/last sync)
- A shields.io badge preview
- A button to copy the badge's Markdown code

#### Chart View
Interactive time-series visualization showing:
- **Line charts** for each repository displaying clone trends over time
- **Dual metrics**: Both total clones (blue) and unique clones (green) on the same chart
- **Time period filters**: View data for the last 7 days, 30 days, 3 months, or all time
- **Repository filtering**: Focus on specific repositories or view all
- **Responsive design**: Charts adapt to screen size and respect dark/light themes
- **Interactive tooltips**: Hover over data points for detailed daily statistics

<div align="center">
<img width="70%" height="70%" alt="image" src="https://github.com/user-attachments/assets/4d6248ee-292b-41a6-b79d-179c53c8baf7"  />
</div>

#### Additional Features
- **Dark/Light theme toggle** in the top-right corner
- **Search and sorting** functionality for repositories (card view)
- **Repository management** modal for adding/removing tracked repositories
- **Data export/import** functionality for backup and migration
- **"Sync with GitHub"** button that triggers a fresh data pull from the GitHub API

### API Endpoints

- **`GET /api/stats`**

  Returns a JSON array of all clone statistics from the database.

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

- **`GET /api/chart-data?days=<number>&repo=<repo-name>`**

  Returns time-series data formatted for chart visualization.

  **Query Parameters:**
  - `days` (optional): Number of days to include (7, 30, 90, or 0 for all time). Default: 30
  - `repo` (optional): Filter by specific repository name

  **Example:**
  `http://localhost:8000/api/chart-data?days=30&repo=my-repo`

  **Example Response:**
  ```json
  {
      "chart_data": {
          "my-repo": {
              "labels": ["2024-07-01", "2024-07-02", "2024-07-03"],
              "clones": [5, 3, 8],
              "uniques": [4, 2, 6]
          }
      },
      "days_requested": 30,
      "repo_filter": "my-repo"
  }
  ```

- **`GET /api/badge/<repo-name>`**

  Returns a shields.io-style SVG badge displaying the total clone count for the specified repository.

  **Example:**
  `http://localhost:8000/api/badge/reclaimed` returns an SVG badge showing the clone count

## Deployment Options

### Docker Deployment

For production deployments, Docker provides the most flexible and portable solution:

```bash
# Quick start with docker-compose
docker-compose up -d

# Access the dashboard at http://localhost:8080
```

Configure environment variables in a `.env` file:
```bash
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_username
USE_FIRESTORE=false
PORT=8080
```

### Google Cloud App Engine

Deploy to Google Cloud App Engine in minutes. See the complete deployment guide: [gcloud_deploy.md](gcloud_deploy.md)

## Development

### Building from source

```bash
pip install build
python -m build
```

### Installing in development mode

```bash
pip install -e ".[dev]"
```

This installs the package in development mode with additional tools for linting, formatting, and testing.

## License

MIT License - see [LICENSE](LICENSE) file for details.
