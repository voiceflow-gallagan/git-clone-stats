#!/usr/bin/env python3
"""
Database factory to switch between SQLite and Firestore based on environment.
"""

import os
import logging

# Global variable to store the resolved database path
_resolved_db_path = None


def get_resolved_database_path():
    """
    Get the resolved database path, testing the preferred path first and falling back if needed.
    This ensures all database connections use the same working path.
    """
    global _resolved_db_path

    if _resolved_db_path is not None:
        return _resolved_db_path

    logger = logging.getLogger(__name__)

    # Start with the configured path
    primary_path = os.environ.get('DATABASE_PATH', 'github_stats.db')

    # Test if we can use the primary path
    try:
        import sqlite3
        abs_primary_path = os.path.abspath(primary_path)
        parent_dir = os.path.dirname(abs_primary_path) or "."

        # Create parent directory with explicit permissions
        os.makedirs(parent_dir, mode=0o755, exist_ok=True)

        # Test if we can write to the directory
        test_file = os.path.join(parent_dir, ".write_test")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            # Success! Use the primary path
            _resolved_db_path = abs_primary_path
            logger.info(f"Using primary database path: {_resolved_db_path}")
            return _resolved_db_path
        except (OSError, IOError) as write_test_error:
            logger.warning(f"Primary database directory {parent_dir} is not writable: {write_test_error}")

    except Exception as e:
        logger.warning(f"Failed to test primary database path {primary_path}: {e}")

    # Primary path failed, try fallback if enabled
    allow_fallback = os.environ.get("ALLOW_DB_FALLBACK", "").lower() == "true"
    if allow_fallback:
        fallback_path = os.environ.get("DATABASE_FALLBACK_PATH", "/tmp/github_stats.db")
        try:
            fallback_abs = os.path.abspath(fallback_path)
            fallback_dir = os.path.dirname(fallback_abs) or "."
            os.makedirs(fallback_dir, mode=0o755, exist_ok=True)

            # Test fallback path
            test_file = os.path.join(fallback_dir, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)

            _resolved_db_path = fallback_abs
            logger.warning(f"Using fallback database path: {_resolved_db_path}. Data may be ephemeral.")
            return _resolved_db_path
        except Exception as fallback_error:
            logger.error(f"Fallback database path {fallback_path} also failed: {fallback_error}")

    # If we get here, both primary and fallback failed, return primary anyway
    # and let the DatabaseManager handle the error
    _resolved_db_path = os.path.abspath(primary_path)
    logger.error(f"All database paths failed, using primary path anyway: {_resolved_db_path}")
    return _resolved_db_path


def get_database_manager():
    """
    Return appropriate database manager based on environment.

    Priority:
    1. If USE_FIRESTORE env var is set to 'true', use Firestore
    2. If running on GAE (GAE_ENV is set), use Firestore
    3. Otherwise, use SQLite (default)
    """
    logger = logging.getLogger(__name__)

    use_firestore = os.getenv('USE_FIRESTORE', '').lower() == 'true'
    is_gae = os.getenv('GAE_ENV', '').startswith('standard')

    if use_firestore or is_gae:
        try:
            from .firestore_db import FirestoreDatabaseManager
            logger.info("Using Firestore database")
            return FirestoreDatabaseManager()
        except ImportError as e:
            logger.warning(f"Failed to import Firestore: {e}. Falling back to SQLite.")
        except Exception as e:
            logger.warning(f"Failed to initialize Firestore: {e}. Falling back to SQLite.")

    # Default to SQLite using the resolved path
    from .app import DatabaseManager
    logger.info("Using SQLite database")
    resolved_path = get_resolved_database_path()
    return DatabaseManager(resolved_path)
