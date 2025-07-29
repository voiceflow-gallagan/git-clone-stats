#!/usr/bin/env python3
"""
Data models for GitHub repository statistics.

Contains the core data classes used throughout the application.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class CloneRecord:
    """Represents a single clone record with count, timestamp, and unique clones."""
    count: int
    timestamp: str
    uniques: int

    def __str__(self) -> str:
        return f"{self.count} {self.timestamp} {self.uniques}"

    @classmethod
    def from_github_entry(cls, entry: Dict[str, any]) -> 'CloneRecord':
        """Create a CloneRecord from GitHub API response entry."""
        return cls(entry["count"], entry["timestamp"], entry["uniques"])


@dataclass
class ViewRecord:
    """Represents a single view record with count, timestamp, and unique views."""
    count: int
    timestamp: str
    uniques: int

    def __str__(self) -> str:
        return f"{self.count} {self.timestamp} {self.uniques}"

    @classmethod
    def from_github_entry(cls, entry: Dict[str, any]) -> 'ViewRecord':
        """Create a ViewRecord from GitHub API response entry."""
        return cls(entry["count"], entry["timestamp"], entry["uniques"])