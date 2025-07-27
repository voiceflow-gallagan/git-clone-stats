"""
GitHub Repository Clone Statistics Tracker

A modern Python application for tracking and storing GitHub repository clone statistics.
This tool fetches clone data from the GitHub API and maintains historical records in a SQLite database.
"""

__version__ = "1.0.0"
__author__ = "Taylor Wilsdon"
__email__ = "taylor@example.com"

from .app import GitHubStatsTracker, DatabaseManager, CloneRecord, run_sync

__all__ = [
    "GitHubStatsTracker",
    "DatabaseManager",
    "CloneRecord",
    "run_sync",
]
