#!/usr/bin/env python3
"""
Database factory to switch between SQLite and Firestore based on environment.
"""

import os
import logging


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
    
    # Default to SQLite
    from .app import DatabaseManager
    logger.info("Using SQLite database")
    return DatabaseManager(os.environ.get('DATABASE_PATH', 'github_stats.db'))