#!/usr/bin/env python3
"""
GitHub Repository Clone Statistics Tracker

A modern Python application for tracking and storing GitHub repository clone statistics.
This tool fetches clone data from the GitHub API and maintains historical records in a SQLite database.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests


@dataclass
class CloneRecord:
    """Represents a single clone record with count, timestamp, and unique clones."""
    count: int
    timestamp: str
    uniques: int

    def __str__(self) -> str:
        return f"{self.count} {self.timestamp} {self.uniques}"

    @classmethod
    def from_github_entry(cls, entry: Dict) -> 'CloneRecord':
        """Create a CloneRecord from GitHub API response entry."""
        return cls(entry["count"], entry["timestamp"], entry["uniques"])


class DatabaseManager:
    """Handles all database operations for clone statistics."""

    def __init__(self, db_path: str):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = None
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def setup_database(self):
        """Create the necessary tables if they don't exist."""
        try:
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS clone_history (
                        repo TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        count INTEGER NOT NULL,
                        uniques INTEGER NOT NULL,
                        PRIMARY KEY (repo, timestamp)
                    )
                """)
            self.logger.info("Database setup complete.")
        except sqlite3.Error as e:
            self.logger.error(f"Database setup failed: {e}")
            raise

    def get_existing_timestamps(self, repo: str) -> List[str]:
        """Get all existing timestamps for a given repository."""
        try:
            with self.conn:
                cursor = self.conn.execute(
                    "SELECT timestamp FROM clone_history WHERE repo = ?", (repo,)
                )
                return [row['timestamp'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get existing timestamps for {repo}: {e}")
            return []

    def insert_clone_records(self, repo: str, records: List['CloneRecord']):
        """Insert new clone records into the database."""
        if not records:
            return

        insert_data = [
            (repo, record.timestamp, record.count, record.uniques) for record in records
        ]

        try:
            with self.conn:
                self.conn.executemany(
                    "INSERT OR IGNORE INTO clone_history (repo, timestamp, count, uniques) VALUES (?, ?, ?, ?)",
                    insert_data
                )
            self.logger.info(f"Inserted {len(records)} new records for {repo}.")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert clone records for {repo}: {e}")
            raise


class GitHubStatsTracker:
    """Main class for tracking GitHub repository clone statistics."""

    def __init__(self, github_token: str, github_username: str, repos: List[str], db_manager: 'DatabaseManager'):
        """
        Initialize the stats tracker.

        Args:
            github_token: GitHub Personal Access Token
            github_username: GitHub username
            repos: List of repository names to track
            db_manager: Instance of DatabaseManager
        """
        self.github_token = github_token
        self.github_username = github_username
        self.repos = repos
        self.db_manager = db_manager
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        })

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _fetch_clone_data(self, repo: str) -> Dict:
        """Fetch clone data from GitHub API."""
        url = f"https://api.github.com/repos/{self.github_username}/{repo}/traffic/clones"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Error fetching data for {repo}: {e}")
            raise

    def _update_repository(self, repo: str) -> None:
        """Update clone data for a single repository."""
        self.logger.info(f"Updating data for {repo}")

        # Get existing timestamps from DB
        self.logger.info("Reading existing data from database...")
        existing_timestamps = self.db_manager.get_existing_timestamps(repo)
        self.logger.info(f"Found {len(existing_timestamps)} existing records for {repo}")

        # Fetch new data from GitHub
        self.logger.info("Fetching data from GitHub...")
        try:
            github_data = self._fetch_clone_data(repo)
            clone_entries = github_data.get("clones", [])

            # Process new entries
            new_records_to_add = []
            for entry in clone_entries:
                timestamp = entry["timestamp"]
                if timestamp not in existing_timestamps:
                    new_record = CloneRecord.from_github_entry(entry)
                    new_records_to_add.append(new_record)
                    self.logger.debug(f"New record for {repo}: {new_record}")

            # Insert new records into the database
            if new_records_to_add:
                self.db_manager.insert_clone_records(repo, new_records_to_add)
            else:
                self.logger.info(f"No new records to add for {repo}")

            self.logger.info(f"Update for {repo} completed successfully")

        except Exception as e:
            self.logger.error(f"Failed to update {repo}: {e}")
            raise

    def update_all_repositories(self) -> None:
        """Update clone data for all configured repositories."""
        self.logger.info("Starting update for all repositories")

        for repo in self.repos:
            try:
                print("=" * 60)
                print(f"   Updating data for {repo}")
                print("=" * 60)

                self._update_repository(repo)
                print()

            except Exception as e:
                self.logger.error(f"Failed to update {repo}: {e}")
                continue

        self.logger.info("Finished updating all repositories")


def load_configuration() -> Tuple[str, str, List[str], str]:
    """Load configuration from environment variables."""
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set.")

    github_username = os.environ.get('GITHUB_USERNAME')
    if not github_username:
        raise ValueError("GITHUB_USERNAME environment variable not set.")

    # Repository list - could be loaded from config file in the future
    repos = ['reddacted', 'reclaimed', 'google_workspace_mcp', 'netshow']

    db_path = "github_stats.db"

    return github_token, github_username, repos, db_path


def run_sync():
    """Runs the GitHub stats synchronization."""
    logger = logging.getLogger(__name__)
    try:
        # Load configuration
        github_token, github_username, repos, db_path = load_configuration()

        # Setup and run tracker
        with DatabaseManager(db_path) as db_manager:
            db_manager.setup_database()
            tracker = GitHubStatsTracker(github_token, github_username, repos, db_manager)
            tracker.update_all_repositories()
        logger.info("Sync successful")
        return True, "Sync successful"
    except Exception as e:
        logger.error(f"Application error: {e}")
        return False, str(e)


def main() -> None:
    """Main entry point of the application."""
    try:
        run_sync()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")


if __name__ == "__main__":
    main()