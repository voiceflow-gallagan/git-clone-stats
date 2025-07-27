# GitHub Repository Clone Statistics Tracker

A modern Python application for tracking and storing GitHub repository clone statistics. This tool fetches clone data from the GitHub API and maintains historical records in a SQLite database. It runs as an always on service and periodically fetches clone stats (total and unique) and displays them in an easy to use dashboard with shields.io badges available for use.

## Features

- Fetches repository clone statistics (total clones and unique cloners) from the GitHub API
- Stores historical data in a SQLite database for robust and efficient querying
- Avoids duplicate entries by only recording new data
- Web dashboard with automatic background synchronization
- CLI interface with subcommands for sync and server operations
- PyPI-ready packaging with modern Python tooling support
- Compatible with uv for fast installation and execution

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

#### Additional Features
- **Dark/Light theme toggle** in the top-right corner
- **Search and sorting** functionality for repositories (card view)
- **Repository management** modal for adding/removing tracked repositories
- **Data export/import** functionality for backup and migration
- **"Sync with GitHub"** button that triggers a fresh data pull from the GitHub API

### API Endpoints

- **`GET /stats`**

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

- **`GET /chart-data?days=<number>&repo=<repo-name>`**

  Returns time-series data formatted for chart visualization.

  **Query Parameters:**
  - `days` (optional): Number of days to include (7, 30, 90, or 0 for all time). Default: 30
  - `repo` (optional): Filter by specific repository name

  **Example:**
  `http://localhost:8000/chart-data?days=30&repo=my-repo`

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

- **`GET /badge/<repo-name>`**

  Returns a shields.io badge displaying the total clone count for the specified repository.

  **Example:**
  `http://localhost:8000/badge/reclaimed` will redirect to:
  `https://img.shields.io/badge/clones-123-blue` (where 123 is the total clone count)

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