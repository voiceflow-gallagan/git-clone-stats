#!/usr/bin/env python3
"""
Database adapter for server.py to handle both SQLite and Firestore operations.
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class DatabaseAdapter:
    """Base adapter interface for database operations."""

    def get_stats_for_repo(self, repo_name: str) -> dict:
        raise NotImplementedError

    def get_all_repos_summary(self) -> List[dict]:
        raise NotImplementedError

    def get_repo_history(self, repo_name: str, history_type: str = 'clones', days: int = 30) -> List[dict]:
        raise NotImplementedError


class SQLiteAdapter(DatabaseAdapter):
    """SQLite adapter for local database operations."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        # Use absolute path to ensure we're accessing the right database and directory exists
        raw_path = os.environ.get('DATABASE_PATH', 'github_stats.db')
        abs_path = os.path.abspath(raw_path)
        try:
            os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        except Exception:
            # Best-effort; failures will surface on connect
            pass
        self.db_path = abs_path

    def get_stats_for_repo(self, repo_name: str) -> dict:
        """Retrieve statistics for a single repository."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get all-time clone stats
            cursor = conn.execute(
                "SELECT SUM(count) as total_clones, SUM(uniques) as total_unique_clones "
                "FROM clone_history WHERE repo = ?",
                (repo_name,)
            )
            clone_row = cursor.fetchone()

            # Get all-time view stats
            cursor = conn.execute(
                "SELECT SUM(count) as total_views, SUM(uniques) as total_unique_views "
                "FROM view_history WHERE repo = ?",
                (repo_name,)
            )
            view_row = cursor.fetchone()

            # Get last 14 days clone stats
            cursor = conn.execute(
                "SELECT SUM(count) as recent_clones, SUM(uniques) as recent_unique_clones "
                "FROM clone_history WHERE repo = ? AND datetime(timestamp) >= datetime('now', '-14 days')",
                (repo_name,)
            )
            recent_clone_row = cursor.fetchone()

            # Get last 14 days view stats
            cursor = conn.execute(
                "SELECT SUM(count) as recent_views, SUM(uniques) as recent_unique_views "
                "FROM view_history WHERE repo = ? AND datetime(timestamp) >= datetime('now', '-14 days')",
                (repo_name,)
            )
            recent_view_row = cursor.fetchone()

            # Get sync timestamp and first collected timestamp
            cursor = conn.execute(
                "SELECT tr.last_sync, "
                "MIN(COALESCE(ch.timestamp, vh.timestamp)) as first_collected "
                "FROM tracked_repos tr "
                "LEFT JOIN clone_history ch ON tr.repo_name = ch.repo "
                "LEFT JOIN view_history vh ON tr.repo_name = vh.repo "
                "WHERE tr.repo_name = ? "
                "GROUP BY tr.repo_name",
                (repo_name,)
            )
            timestamp_row = cursor.fetchone()

            return {
                "repo": repo_name,
                "total_clones": clone_row["total_clones"] or 0,
                "total_unique_clones": clone_row["total_unique_clones"] or 0,
                "total_views": view_row["total_views"] or 0,
                "total_unique_views": view_row["total_unique_views"] or 0,
                "last_14_days_clones": recent_clone_row["recent_clones"] or 0,
                "last_14_days_unique_clones": recent_clone_row["recent_unique_clones"] or 0,
                "last_14_days_views": recent_view_row["recent_views"] or 0,
                "last_14_days_unique_views": recent_view_row["recent_unique_views"] or 0,
                "last_updated": timestamp_row["last_sync"] if timestamp_row else None,
                "first_collected": timestamp_row["first_collected"] if timestamp_row else None
            }

    def get_all_repos_summary(self) -> List[dict]:
        """Get summary statistics for all repositories."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get all tracked repos with both total and recent stats using separate subqueries to avoid cartesian product
            cursor = conn.execute("""
                SELECT
                    tr.repo_name,
                    -- Total all-time stats from subqueries
                    COALESCE(cs.total_clones, 0) as total_clones,
                    COALESCE(cs.total_unique_clones, 0) as total_unique_clones,
                    COALESCE(vs.total_views, 0) as total_views,
                    COALESCE(vs.total_unique_views, 0) as total_unique_views,
                    -- Recent 14-day stats
                    COALESCE(cs.last_14_days_clones, 0) as last_14_days_clones,
                    COALESCE(cs.last_14_days_unique_clones, 0) as last_14_days_unique_clones,
                    COALESCE(vs.last_14_days_views, 0) as last_14_days_views,
                    COALESCE(vs.last_14_days_unique_views, 0) as last_14_days_unique_views,
                    -- Star count
                    COALESCE(rs.star_count, 0) as star_count,
                    -- Timestamps - use actual sync time and earliest data point
                    tr.last_sync as last_updated,
                    COALESCE(cs.first_clone_timestamp, vs.first_view_timestamp) as first_collected
                FROM tracked_repos tr
                LEFT JOIN (
                    SELECT
                        repo,
                        SUM(count) as total_clones,
                        SUM(uniques) as total_unique_clones,
                        SUM(CASE WHEN datetime(timestamp) >= datetime('now', '-14 days') THEN count ELSE 0 END) as last_14_days_clones,
                        SUM(CASE WHEN datetime(timestamp) >= datetime('now', '-14 days') THEN uniques ELSE 0 END) as last_14_days_unique_clones,
                        MAX(timestamp) as last_clone_timestamp,
                        MIN(timestamp) as first_clone_timestamp
                    FROM clone_history
                    GROUP BY repo
                ) cs ON tr.repo_name = cs.repo
                LEFT JOIN (
                    SELECT
                        repo,
                        SUM(count) as total_views,
                        SUM(uniques) as total_unique_views,
                        SUM(CASE WHEN datetime(timestamp) >= datetime('now', '-14 days') THEN count ELSE 0 END) as last_14_days_views,
                        SUM(CASE WHEN datetime(timestamp) >= datetime('now', '-14 days') THEN uniques ELSE 0 END) as last_14_days_unique_views,
                        MAX(timestamp) as last_view_timestamp,
                        MIN(timestamp) as first_view_timestamp
                    FROM view_history
                    GROUP BY repo
                ) vs ON tr.repo_name = vs.repo
                LEFT JOIN repo_stars rs ON tr.repo_name = rs.repo
                WHERE tr.is_active = 1
                ORDER BY tr.repo_name
            """)

            results = []
            for row in cursor:
                results.append({
                    "repo": row["repo_name"],
                    "total_clones": row["total_clones"],
                    "total_unique_clones": row["total_unique_clones"],
                    "total_views": row["total_views"],
                    "total_unique_views": row["total_unique_views"],
                    "last_14_days_clones": row["last_14_days_clones"],
                    "last_14_days_unique_clones": row["last_14_days_unique_clones"],
                    "last_14_days_views": row["last_14_days_views"],
                    "last_14_days_unique_views": row["last_14_days_unique_views"],
                    "star_count": row["star_count"],
                    "last_updated": row["last_updated"],
                    "first_collected": row["first_collected"]
                })

            return results

    def get_repo_history(self, repo_name: str, history_type: str = 'clones', days: int = 30) -> List[dict]:
        """Get historical data for a repository."""
        table = 'clone_history' if history_type == 'clones' else 'view_history'

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT timestamp, count, uniques FROM {table} "
                f"WHERE repo = ? ORDER BY timestamp DESC LIMIT ?",
                (repo_name, days)
            )

            results = []
            for row in cursor:
                results.append({
                    "timestamp": row["timestamp"],
                    "count": row["count"],
                    "uniques": row["uniques"]
                })

            return list(reversed(results))


class FirestoreAdapter(DatabaseAdapter):
    """Firestore adapter for cloud database operations."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_stats_for_repo(self, repo_name: str) -> dict:
        """Retrieve statistics for a single repository."""
        # Get aggregated data
        agg_data = self.db_manager.get_aggregated_data(repo_name) or {}

        # Get all-time stats from history
        clone_history = self.db_manager.get_clone_history(repo_name, days=9999)
        view_history = self.db_manager.get_view_history(repo_name, days=9999)

        total_clones = sum(record['count'] for record in clone_history)
        total_unique_clones = sum(record['uniques'] for record in clone_history)
        total_views = sum(record['count'] for record in view_history)
        total_unique_views = sum(record['uniques'] for record in view_history)

        return {
            "repo": repo_name,
            "total_clones": total_clones,
            "total_unique_clones": total_unique_clones,
            "total_views": total_views,
            "total_unique_views": total_unique_views,
            "last_14_days_clones": agg_data.get('total_clones', 0),
            "last_14_days_unique_clones": agg_data.get('unique_clones', 0),
            "last_14_days_views": agg_data.get('total_views', 0),
            "last_14_days_unique_views": agg_data.get('unique_views', 0),
            "last_updated": agg_data.get('last_updated')
        }

    def get_all_repos_summary(self) -> List[dict]:
        """Get summary statistics for all repositories."""
        repos = self.db_manager.get_tracked_repos()
        results = []

        for repo in repos:
            agg_data = self.db_manager.get_aggregated_data(repo) or {}
            results.append({
                "repo": repo,
                "last_14_days_clones": agg_data.get('total_clones', 0),
                "last_14_days_unique_clones": agg_data.get('unique_clones', 0),
                "last_14_days_views": agg_data.get('total_views', 0),
                "last_14_days_unique_views": agg_data.get('unique_views', 0),
                "last_updated": agg_data.get('last_updated')
            })

        return sorted(results, key=lambda x: x['repo'])

    def get_repo_history(self, repo_name: str, history_type: str = 'clones', days: int = 30) -> List[dict]:
        """Get historical data for a repository."""
        if history_type == 'clones':
            history = self.db_manager.get_clone_history(repo_name, days)
        else:
            history = self.db_manager.get_view_history(repo_name, days)

        results = []
        for record in history:
            results.append({
                "timestamp": record["timestamp"],
                "count": record["count"],
                "uniques": record["uniques"]
            })

        return results


def get_database_adapter(db_manager) -> DatabaseAdapter:
    """Return appropriate database adapter based on the manager type."""
    if hasattr(db_manager, 'db'):  # Firestore has a 'db' attribute
        return FirestoreAdapter(db_manager)
    else:
        return SQLiteAdapter(db_manager)
