"""
__init__.py — creates and configures the Flask application.

This file is the entry point for the flask_app package. Its job is to:
  1. Load configuration (API keys from .env)
  2. Set up the database (create tables, load CSV data)
  3. Register routes (the URL paths the app responds to)
  4. Set up Socket.IO (for real-time chat)
  5. Return the configured app so app.py can run it
"""

import os
from flask import Flask
from flask_socketio import SocketIO
from dotenv import load_dotenv, find_dotenv

# Create the SocketIO instance here at module level.
socketio = SocketIO()


def create_app():
    """
    Build and return the configured Flask application.

    Returns:
        tuple: (app, socketio) — both are needed to run the server.
    """

    # find_dotenv(usecwd=True) يضمن العثور على ملف .env وتحميل المتغيرات بنجاح
    load_dotenv(find_dotenv(usecwd=True))

    app = Flask(__name__)

    # The secret_key is used to cryptographically sign session cookies.
    app.secret_key = 'dev-key-change-for-production'

    # Set up the database: create tables and load CSV data
    from flask_app.utils.database import database
    db = database()
    print("Setting up database...")
    db.createTables(purge=True)
    app.db = db
    print("Database ready.")

    # Connect Socket.IO to the Flask app
    socketio.init_app(app)

    # Register routes and socket events inside the app context.
    with app.app_context():
        from flask_app import routes
        from flask_app.utils import socket_events

        # Inject the database into the routes and socket_events modules
        routes.db = db
        socket_events.db = db

    # Prevent browsers from caching old versions of pages during development
    @app.after_request
    def disable_cache(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app, socketio