#!/usr/bin/env python3
"""
Main entry point for the git-clone-stats application on App Engine.
"""

import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from git_clone_stats.server import main

if __name__ == "__main__":
    main()