#!/usr/bin/env python3
"""
SatVision Backend - Entry Point Script

Refactored monolithic server.py into a modular, production-grade Flask application.
Implements Application Factory pattern with clean separation of concerns.

Usage:
    python main.py
"""

from src import config
from src.app import create_app


def main():
    """Main entry point for the backend server."""
    print("[SatVision] Production Backend Running...", flush=True)
    
    # Create application instance
    app = create_app()
    
    # Run Flask application server
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        threaded=config.FLASK_THREADED,
        debug=False
    )


if __name__ == '__main__':
    main()