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
from http import HTTPStatus
from pathlib import Path

from .app import run_sync

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

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        if self.path == '/stats':
            self.send_stats()
        elif self.path.startswith('/badge/'):
            match = re.match(r'/badge/([\w-]+)', self.path)
            if match:
                repo_name = match.group(1)
                self.send_badge(repo_name)
            else:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid badge URL format. Use /badge/<repo-name>")
        else:
            super().do_GET()

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/sync':
            self.send_sync_response()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found. Use /sync")

    def send_sync_response(self):
        """Run the sync and send a response."""
        logger.info("Sync requested from web UI.")
        success, message = run_sync()
        status = HTTPStatus.OK if success else HTTPStatus.INTERNAL_SERVER_ERROR

        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"success": success, "message": message}
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def get_stats_for_repo(self, repo_name: str) -> dict:
        """Retrieve statistics for a single repository."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT SUM(count) as total_clones, SUM(uniques) as total_uniques FROM clone_history WHERE repo = ?",
                    (repo_name,)
                )
                row = cursor.fetchone()
                if row and row['total_clones'] is not None:
                    return dict(row)
                return {"total_clones": 0, "total_uniques": 0}
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
                cursor = conn.execute("SELECT repo, timestamp, count, uniques FROM clone_history ORDER BY repo, timestamp")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
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
        response_data = {
            "stats": stats,
            "github_username": github_username
        }

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data, indent=4).encode('utf-8'))

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


def run_server(port=8124):
    """Run the web server."""
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