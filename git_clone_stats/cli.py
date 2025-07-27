#!/usr/bin/env python3
"""
Command-line interface for git-clone-stats.
"""

import argparse
import sys
from typing import Optional

from .app import main as app_main


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="git-clone-stats",
        description="GitHub repository clone statistics tracker"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sync command
    subparsers.add_parser("sync", help="Synchronize clone statistics from GitHub")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the web dashboard server")
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )

    return parser


def main(argv: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "sync":
        app_main()
        return 0
    elif args.command == "server":
        from .server import run_server
        try:
            run_server(port=args.port)
            return 0
        except KeyboardInterrupt:
            print("\nServer stopped by user")
            return 0
        except Exception as e:
            print(f"Server error: {e}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
