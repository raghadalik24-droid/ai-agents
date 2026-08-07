"""
app.py — the entry point for the application.

Run this file to start the web server:
    python app.py

Then open your browser to: http://localhost:8080
"""
import os
from dotenv import load_dotenv, find_dotenv

# تحميل واختبار ملف .env مباشرة
load_dotenv(find_dotenv(usecwd=True))

print("="*40)
print("TESTING API KEY:", os.getenv("OPENROUTER_API_KEY"))
print("="*40)

from flask_app import create_app

# Build the app and get the socketio instance back
app, socketio = create_app()

if __name__ == "__main__":
    print("Starting AI Resume Agent...")
    print("Open your browser to: http://localhost:8080")
    socketio.run(app, host='0.0.0.0', port=8080, debug=True, use_reloader=False)