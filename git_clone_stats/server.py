#!/usr/bin/env python3
"""
GitHub Repository Clone Statistics Web Server

A simple web server to expose the collected clone statistics via a JSON API.
"""

import http.server
import json
import logging
import os
import re
import sqlite3
import threading
import time
import urllib.parse
from http import HTTPStatus
from pathlib import Path

from .app import run_sync, DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = "github_stats.db"


class StatsRequestHandler(http.server.SimpleHTTPRequestHandler):
    """A custom request handler to serve clone statistics."""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve static files from
        static_dir = Path(__file__).parent / "static"
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def _send_json_response(self, data: dict, status: HTTPStatus = HTTPStatus.OK):
        """Send a JSON response with consistent headers."""
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def _send_json_error(self, message: str, status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR):
        """Send a JSON error response."""
        self._send_json_response({"success": False, "message": message}, status)

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        if self.path == '/stats':
            self.send_stats()
        elif self.path == '/tracked-repos':
            self.send_tracked_repos()
        elif self.path == '/export':
            self.send_export()
        elif self.path.startswith('/chart-data'):
            self.send_chart_data()
        elif self.path.startswith('/badge/'):
            match = re.match(r'/badge/([\w-]+)', self.path)
            if match:
                repo_name = match.group(1)
                self.send_badge(repo_name)
            else:
                self.send_error(
                    HTTPStatus.BAD_REQUEST, "Invalid badge URL format. Use /badge/<repo-name>"
                )
        else:
            super().do_GET()

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/sync':
            self.send_sync_response()
        elif self.path == '/tracked-repos':
            self.handle_add_repo()
        elif self.path == '/import':
            self.handle_import()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def do_DELETE(self):
        """Handle DELETE requests."""
        if self.path.startswith('/tracked-repos/'):
            match = re.match(r'/tracked-repos/([\w-]+)', self.path)
            if match:
                repo_name = match.group(1)
                self.handle_remove_repo(repo_name)
            else:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid repo URL format")
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def send_sync_response(self):
        """Run the sync and send a response."""
        logger.info("Sync requested from web UI.")
        success, message = run_sync()
        status = HTTPStatus.OK if success else HTTPStatus.INTERNAL_SERVER_ERROR
        self._send_json_response({"success": success, "message": message}, status)

    def get_stats_for_repo(self, repo_name: str) -> dict:
        """Retrieve statistics for a single repository."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT SUM(count) as total_clones, SUM(uniques) as total_uniques "
                    "FROM clone_history WHERE repo = ?",
                    (repo_name,)
                )
                row = cursor.fetchone()
                return dict(row) if row and row['total_clones'] is not None else {
                    "total_clones": 0, "total_uniques": 0
                }
        except sqlite3.Error as e:
            logger.error(f"Database error for repo {repo_name}: {e}")
            return None

    def send_badge(self, repo_name: str):
        """Redirect to a shields.io badge for the repo."""
        stats = self.get_stats_for_repo(repo_name)
        if stats is None:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to retrieve stats from the database.")
            return

        total_clones = stats.get('total_clones', 0)
        message = f"{total_clones}"
        label = "clones"
        color = "blue"

        badge_url = f"https://img.shields.io/badge/{label}-{message}-{color}"

        self.send_response(HTTPStatus.FOUND)
        self.send_header('Location', badge_url)
        self.end_headers()

    def get_all_stats(self):
        """Retrieve all statistics from the database."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row

                # Get clone history
                cursor = conn.execute(
                    "SELECT repo, timestamp, count, uniques FROM clone_history ORDER BY repo, timestamp"
                )
                clone_rows = cursor.fetchall()

                # Get star counts
                cursor = conn.execute("SELECT repo, star_count FROM repo_stars")
                star_rows = cursor.fetchall()
                star_counts = {
                    row['repo']: row['star_count'] for row in star_rows
                }

                # Combine the data
                stats = []
                for row in clone_rows:
                    stat = dict(row)
                    stat['star_count'] = star_counts.get(row['repo'], 0)
                    stats.append(stat)

                return stats
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return None

    def send_stats(self):
        """Send the clone statistics as a JSON response."""
        stats = self.get_all_stats()

        if stats is None:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to retrieve stats from the database.")
            return

        github_username = os.environ.get('GITHUB_USERNAME', '')
        self._send_json_response({
            "stats": stats,
            "github_username": github_username
        })

    def send_tracked_repos(self):
        """Send the list of tracked repositories."""
        try:
            with DatabaseManager(DB_PATH) as db_manager:
                db_manager.setup_database()
                tracked_repos = db_manager.get_tracked_repos()

            self._send_json_response({"tracked_repos": tracked_repos})
        except Exception as e:
            logger.error(f"Error getting tracked repos: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to get tracked repositories")

    def handle_add_repo(self):
        """Handle adding a new tracked repository."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            repo_name = data.get('repo_name', '').strip()
            if not repo_name:
                self.send_error(HTTPStatus.BAD_REQUEST, "Repository name is required")
                return

            with DatabaseManager(DB_PATH) as db_manager:
                db_manager.setup_database()
                success = db_manager.add_tracked_repo(repo_name)

            if success:
                self._send_json_response({
                    "success": True,
                    "message": f"Repository {repo_name} added successfully"
                })
            else:
                self._send_json_error("Failed to add repository")

        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON data")
        except Exception as e:
            logger.error(f"Error adding repo: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to add repository")

    def handle_remove_repo(self, repo_name):
        """Handle removing a tracked repository."""
        try:
            with DatabaseManager(DB_PATH) as db_manager:
                db_manager.setup_database()
                success = db_manager.remove_tracked_repo(repo_name)

            if success:
                self._send_json_response({
                    "success": True,
                    "message": f"Repository {repo_name} removed successfully"
                })
            else:
                self._send_json_error("Failed to remove repository")

        except Exception as e:
            logger.error(f"Error removing repo: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to remove repository")

    def send_chart_data(self):
        """Send chart data for time-series visualization."""
        try:
            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            # Get parameters with defaults
            days = int(query_params.get('days', ['30'])[0])  # Default to 30 days
            repo_filter = query_params.get('repo', [None])[0]  # Optional repo filter

            # Calculate date threshold
            from datetime import datetime, timedelta
            if days > 0:
                date_threshold = datetime.now() - timedelta(days=days)
                date_threshold_str = date_threshold.isoformat()
            else:
                date_threshold_str = None  # Show all data

            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row

                # Build query
                query = "SELECT repo, timestamp, count, uniques FROM clone_history"
                params = []

                where_conditions = []
                if date_threshold_str:
                    where_conditions.append("timestamp >= ?")
                    params.append(date_threshold_str)

                if repo_filter:
                    where_conditions.append("repo = ?")
                    params.append(repo_filter)

                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)

                query += " ORDER BY repo, timestamp"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # Organize data by repository
                chart_data = {}
                for row in rows:
                    repo = row['repo']
                    if repo not in chart_data:
                        chart_data[repo] = {
                            'labels': [],
                            'clones': [],
                            'uniques': []
                        }

                    # Format timestamp for display
                    timestamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                    formatted_date = timestamp.strftime('%Y-%m-%d')

                    chart_data[repo]['labels'].append(formatted_date)
                    chart_data[repo]['clones'].append(row['count'])
                    chart_data[repo]['uniques'].append(row['uniques'])

            self._send_json_response({
                "chart_data": chart_data,
                "days_requested": days,
                "repo_filter": repo_filter
            })

        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to retrieve chart data")

    def send_export(self):
        """Export database as JSON."""
        try:
            with DatabaseManager(DB_PATH) as db_manager:
                db_manager.setup_database()
                export_data = db_manager.export_database()

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=github_stats_backup_{export_data['export_timestamp'][:10]}.json"
            )
            self.end_headers()
            self.wfile.write(json.dumps(export_data, indent=2).encode('utf-8'))

        except Exception as e:
            logger.error(f"Error exporting database: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to export database")

    def handle_import(self):
        """Handle database import from JSON."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(HTTPStatus.BAD_REQUEST, "No data provided")
                return

            post_data = self.rfile.read(content_length)

            # Check if it's form data (file upload) or JSON
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                # Handle file upload
                # Simple multipart parsing (for file uploads)
                boundary = content_type.split('boundary=')[1].encode()
                parts = post_data.split(b'--' + boundary)

                file_data = None
                replace_existing = False

                for part in parts:
                    if b'Content-Disposition' in part and b'name="file"' in part:
                        # Extract file content
                        content_start = part.find(b'\r\n\r\n') + 4
                        if content_start > 3:
                            file_data = part[content_start:].rstrip(b'\r\n')
                    elif b'name="replace_existing"' in part:
                        content_start = part.find(b'\r\n\r\n') + 4
                        if content_start > 3:
                            value = part[content_start:].rstrip(b'\r\n').decode('utf-8')
                            replace_existing = value.lower() == 'true'

                if not file_data:
                    self.send_error(HTTPStatus.BAD_REQUEST, "No file data found")
                    return

                import_data = json.loads(file_data.decode('utf-8'))
            else:
                # Handle direct JSON
                import_data = json.loads(post_data.decode('utf-8'))
                replace_existing = import_data.get('replace_existing', False)

            # Validate import data structure
            required_keys = ['clone_history', 'tracked_repos', 'repo_stars']
            if not all(key in import_data for key in required_keys):
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid backup file format")
                return

            with DatabaseManager(DB_PATH) as db_manager:
                db_manager.setup_database()
                success = db_manager.import_database(import_data, replace_existing)

            if success:
                self._send_json_response({
                    "success": True,
                    "message": "Database imported successfully"
                })
            else:
                self._send_json_error("Failed to import database")

        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON data")
        except Exception as e:
            logger.error(f"Error importing database: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to import database")


def run_background_sync():
    """Periodically run the sync task based on the configured interval."""
    interval_str = os.environ.get("SYNC_INTERVAL", "daily").lower()
    intervals = {"daily": 86400, "weekly": 604800, "biweekly": 1209600}
    sleep_duration = intervals.get(interval_str, 86400)

    logger.info(f"Background sync configured with a {interval_str} interval.")

    # Wait a few seconds for the server to start before the initial sync.
    time.sleep(5)
    logger.info("Initial background sync started.")
    run_sync()
    logger.info("Initial background sync finished.")

    while True:
        logger.info(f"Background sync sleeping for {sleep_duration} seconds.")
        time.sleep(sleep_duration)
        logger.info("Background sync started.")
        run_sync()
        logger.info("Background sync finished.")


def run_server(port=None):
    """Run the web server."""
    if port is None:
        port = int(os.environ.get("PORT", 8000))
    
    # Start the background sync in a separate thread
    sync_thread = threading.Thread(target=run_background_sync, daemon=True)
    sync_thread.start()

    with http.server.HTTPServer(("", port), StatsRequestHandler) as httpd:
        logger.info(f"Serving at port {port}")
        logger.info(f"Access the UI at http://localhost:{port}")
        httpd.serve_forever()


def main():
    """Main entry point for the server script."""
    run_server()


if __name__ == "__main__":
    main()
