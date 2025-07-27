#!/usr/bin/env python3
"""
GitHub Repository Clone Statistics Tracker

A modern Python application for tracking and storing GitHub repository clone statistics.
This tool fetches clone data from the GitHub API and maintains historical records in a SQLite database.
"""

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
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS tracked_repos (
                        repo_name TEXT PRIMARY KEY,
                        added_at TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1
                    )
                """)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS repo_stars (
                        repo TEXT PRIMARY KEY,
                        star_count INTEGER NOT NULL,
                        last_updated TEXT NOT NULL
                    )
                """)
            self.logger.info("Database setup complete.")
        except sqlite3.Error as e:
            self.logger.error(f"Database setup failed: {e}")
            raise

    def _execute_query(self, query: str, params: tuple = (), fetch_all: bool = True):
        """Execute a database query with consistent error handling."""
        try:
            with self.conn:
                cursor = self.conn.execute(query, params)
                if fetch_all:
                    return cursor.fetchall()
                return cursor.fetchone()
        except sqlite3.Error as e:
            self.logger.error(f"Database query failed: {e}")
            return [] if fetch_all else None

    def get_existing_timestamps(self, repo: str) -> List[str]:
        """Get all existing timestamps for a given repository."""
        rows = self._execute_query(
            "SELECT timestamp FROM clone_history WHERE repo = ?",
            (repo,)
        )
        return [row['timestamp'] for row in rows] if rows else []

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

    def get_tracked_repos(self) -> List[str]:
        """Get all actively tracked repositories."""
        rows = self._execute_query(
            "SELECT repo_name FROM tracked_repos WHERE is_active = 1"
        )
        return [row[0] for row in rows] if rows else []

    def add_tracked_repo(self, repo_name: str) -> bool:
        """Add a repository to tracking."""
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO tracked_repos (repo_name, added_at, is_active) VALUES (?, ?, 1)",
                    (repo_name, datetime.now().isoformat())
                )
            self.logger.info(f"Added {repo_name} to tracked repos.")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to add tracked repo {repo_name}: {e}")
            return False

    def remove_tracked_repo(self, repo_name: str) -> bool:
        """Remove a repository from tracking."""
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE tracked_repos SET is_active = 0 WHERE repo_name = ?",
                    (repo_name,)
                )
            self.logger.info(f"Removed {repo_name} from tracked repos.")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to remove tracked repo {repo_name}: {e}")
            return False

    def update_repo_stars(self, repo: str, star_count: int) -> bool:
        """Update star count for a repository."""
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO repo_stars (repo, star_count, last_updated) VALUES (?, ?, ?)",
                    (repo, star_count, datetime.now().isoformat())
                )
            self.logger.info(f"Updated star count for {repo}: {star_count}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update star count for {repo}: {e}")
            return False

    def get_repo_stars(self, repo: str) -> Optional[int]:
        """Get star count for a repository."""
        row = self._execute_query(
            "SELECT star_count FROM repo_stars WHERE repo = ?",
            (repo,),
            fetch_all=False
        )
        return row[0] if row else None

    def export_database(self) -> Dict:
        """Export the complete database to a dictionary."""
        try:
            with self.conn:
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "version": "1.0",
                    "clone_history": [],
                    "tracked_repos": [],
                    "repo_stars": []
                }

                # Export clone history
                cursor = self.conn.execute(
                    "SELECT repo, timestamp, count, uniques FROM clone_history ORDER BY repo, timestamp"
                )
                for row in cursor.fetchall():
                    export_data["clone_history"].append({
                        "repo": row["repo"],
                        "timestamp": row["timestamp"],
                        "count": row["count"],
                        "uniques": row["uniques"]
                    })

                # Export tracked repos
                cursor = self.conn.execute("SELECT repo_name, added_at, is_active FROM tracked_repos")
                for row in cursor.fetchall():
                    export_data["tracked_repos"].append({
                        "repo_name": row["repo_name"],
                        "added_at": row["added_at"],
                        "is_active": row["is_active"]
                    })

                # Export star counts
                cursor = self.conn.execute("SELECT repo, star_count, last_updated FROM repo_stars")
                for row in cursor.fetchall():
                    export_data["repo_stars"].append({
                        "repo": row["repo"],
                        "star_count": row["star_count"],
                        "last_updated": row["last_updated"]
                    })

                self.logger.info(
                    f"Database exported successfully with {len(export_data['clone_history'])} clone records, "
                    f"{len(export_data['tracked_repos'])} tracked repos, "
                    f"and {len(export_data['repo_stars'])} star records"
                )
                return export_data

        except sqlite3.Error as e:
            self.logger.error(f"Failed to export database: {e}")
            raise

    def import_database(self, import_data: Dict, replace_existing: bool = False) -> bool:
        """Import data from a dictionary into the database."""
        try:
            if replace_existing:
                self.logger.info("Clearing existing data before import...")
                with self.conn:
                    self.conn.execute("DELETE FROM clone_history")
                    self.conn.execute("DELETE FROM tracked_repos")
                    self.conn.execute("DELETE FROM repo_stars")

            # Import clone history
            clone_records = import_data.get("clone_history", [])
            if clone_records:
                with self.conn:
                    self.conn.executemany(
                        "INSERT OR IGNORE INTO clone_history (repo, timestamp, count, uniques) VALUES (?, ?, ?, ?)",
                        [(record["repo"], record["timestamp"], record["count"], record["uniques"])
                         for record in clone_records]
                    )
                self.logger.info(f"Imported {len(clone_records)} clone history records")

            # Import tracked repos
            tracked_repos = import_data.get("tracked_repos", [])
            if tracked_repos:
                with self.conn:
                    self.conn.executemany(
                        "INSERT OR REPLACE INTO tracked_repos (repo_name, added_at, is_active) VALUES (?, ?, ?)",
                        [(record["repo_name"], record["added_at"], record["is_active"])
                         for record in tracked_repos]
                    )
                self.logger.info(f"Imported {len(tracked_repos)} tracked repo records")

            # Import star counts
            star_records = import_data.get("repo_stars", [])
            if star_records:
                with self.conn:
                    self.conn.executemany(
                        "INSERT OR REPLACE INTO repo_stars (repo, star_count, last_updated) VALUES (?, ?, ?)",
                        [(record["repo"], record["star_count"], record["last_updated"])
                         for record in star_records]
                    )
                self.logger.info(f"Imported {len(star_records)} star count records")

            self.logger.info("Database import completed successfully")
            return True

        except (sqlite3.Error, KeyError, TypeError) as e:
            self.logger.error(f"Failed to import database: {e}")
            return False


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

    def _fetch_repo_metadata(self, repo: str) -> Dict:
        """Fetch repository metadata from GitHub API."""
        url = f"https://api.github.com/repos/{self.github_username}/{repo}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Error fetching metadata for {repo}: {e}")
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
            # Fetch clone data
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

            # Fetch and update star count
            self.logger.info("Fetching repository metadata...")
            metadata = self._fetch_repo_metadata(repo)
            star_count = metadata.get("stargazers_count", 0)
            self.db_manager.update_repo_stars(repo, star_count)

            self.logger.info(f"Update for {repo} completed successfully")

        except Exception as e:
            self.logger.error(f"Failed to update {repo}: {e}")
            raise

    def update_all_repositories(self) -> None:
        """Update clone data for all configured repositories."""
        self.logger.info("Starting update for all repositories")

        # Get tracked repos from database if available, otherwise use configured repos
        tracked_repos = self.db_manager.get_tracked_repos()
        repos_to_update = tracked_repos if tracked_repos else self.repos

        for repo in repos_to_update:
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

    # Default repository list (only used for initial setup)
    repos = []

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
            # No default repos to migrate since repos list is empty
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
