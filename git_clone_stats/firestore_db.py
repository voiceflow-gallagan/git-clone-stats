#!/usr/bin/env python3
"""
Firestore database manager for Google App Engine deployment.
"""

import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from google.cloud import firestore
from .models import CloneRecord, ViewRecord


class FirestoreDatabaseManager:
    """Handles all database operations for clone statistics using Firestore."""

    def __init__(self):
        """Initialize the Firestore database manager."""
        self.db = firestore.Client()
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def setup_database(self):
        """Initialize collections - Firestore creates them automatically."""
        self.logger.info("Firestore collections will be created automatically")

    def upsert_clone_records(self, repo: str, records: List[CloneRecord]):
        """Insert or update multiple clone records."""
        batch = self.db.batch()
        collection = self.db.collection('clone_history')
        
        for record in records:
            doc_id = f"{repo}_{record.timestamp}"
            doc_ref = collection.document(doc_id)
            batch.set(doc_ref, {
                'repo': repo,
                'timestamp': record.timestamp,
                'count': record.count,
                'uniques': record.uniques
            })
        
        batch.commit()
        self.logger.info(f"Upserted {len(records)} clone records for {repo}")

    def upsert_view_records(self, repo: str, records: List[ViewRecord]):
        """Insert or update multiple view records."""
        batch = self.db.batch()
        collection = self.db.collection('view_history')
        
        for record in records:
            doc_id = f"{repo}_{record.timestamp}"
            doc_ref = collection.document(doc_id)
            batch.set(doc_ref, {
                'repo': repo,
                'timestamp': record.timestamp,
                'count': record.count,
                'uniques': record.uniques
            })
        
        batch.commit()
        self.logger.info(f"Upserted {len(records)} view records for {repo}")

    def upsert_aggregated_data(self, repo: str, total_clones: Optional[Tuple[int, int]], total_views: Optional[Tuple[int, int]]):
        """Update aggregated clone and view data."""
        doc_ref = self.db.collection('aggregated_data').document(repo)
        data = {'repo': repo, 'last_updated': datetime.utcnow().isoformat()}
        
        if total_clones:
            data.update({
                'total_clones': total_clones[0],
                'unique_clones': total_clones[1]
            })
        
        if total_views:
            data.update({
                'total_views': total_views[0],
                'unique_views': total_views[1]
            })
        
        doc_ref.set(data, merge=True)
        self.logger.info(f"Updated aggregated data for {repo}")

    def update_tracked_repo(self, repo_name: str):
        """Update the last sync time for a tracked repo."""
        doc_ref = self.db.collection('tracked_repos').document(repo_name)
        doc_ref.set({
            'repo_name': repo_name,
            'last_sync': datetime.utcnow().isoformat(),
            'is_active': True
        }, merge=True)

    def get_tracked_repos(self) -> List[Dict[str, str]]:
        """Get all active tracked repositories with their owner types."""
        repos = []
        docs = self.db.collection('tracked_repos').where('is_active', '==', True).stream()
        for doc in docs:
            data = doc.to_dict()
            repos.append({
                "repo_name": doc.id,
                "owner_type": data.get("owner_type", "user")
            })
        return repos
        
    def get_tracked_repo_names(self) -> List[str]:
        """Get just the repository names (for backward compatibility)."""
        repos = self.get_tracked_repos()
        return [repo["repo_name"] for repo in repos]

    def add_tracked_repo(self, repo_name: str, owner_type: str = 'user') -> bool:
        """Add a new repository to track with specified owner type."""
        doc_ref = self.db.collection('tracked_repos').document(repo_name)
        doc_ref.set({
            'repo_name': repo_name,
            'added_at': datetime.utcnow().isoformat(),
            'is_active': True,
            'owner_type': owner_type
        })
        self.logger.info(f"Added {repo_name} to tracked repositories")
        return True

    def remove_tracked_repo(self, repo_name: str) -> bool:
        """Mark a repository as inactive."""
        doc_ref = self.db.collection('tracked_repos').document(repo_name)
        doc_ref.update({'is_active': False})
        self.logger.info(f"Marked {repo_name} as inactive")
        return True

    def get_clone_history(self, repo: str, days: int = 30) -> List[Dict]:
        """Get clone history for a repository."""
        cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_str = cutoff_date.isoformat() + 'Z'
        
        docs = (self.db.collection('clone_history')
                .where('repo', '==', repo)
                .where('timestamp', '>=', cutoff_str)
                .order_by('timestamp')
                .stream())
        
        return [doc.to_dict() for doc in docs]

    def get_view_history(self, repo: str, days: int = 30) -> List[Dict]:
        """Get view history for a repository."""
        cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_str = cutoff_date.isoformat() + 'Z'
        
        docs = (self.db.collection('view_history')
                .where('repo', '==', repo)
                .where('timestamp', '>=', cutoff_str)
                .order_by('timestamp')
                .stream())
        
        return [doc.to_dict() for doc in docs]

    def get_aggregated_data(self, repo: str) -> Optional[Dict]:
        """Get aggregated data for a repository."""
        doc = self.db.collection('aggregated_data').document(repo).get()
        return doc.to_dict() if doc.exists else None