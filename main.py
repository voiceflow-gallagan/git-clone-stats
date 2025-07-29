#!/usr/bin/env python3
"""
Main entry point for the git-clone-stats application on App Engine.
"""

import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from git_clone_stats.server import run_server

if __name__ == "__main__":
    # Run server on port 8000 for local development, 8080 for GAE
    port = int(os.environ.get('PORT', 8000))
    run_server(port=port)