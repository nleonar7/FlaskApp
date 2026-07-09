"""WSGI entry point for PythonAnywhere.

Copy the contents of this file into the WSGI configuration file that
PythonAnywhere creates for your web app (Web tab -> "WSGI configuration file",
a path like /var/www/<username>_pythonanywhere_com_wsgi.py), then edit the
three CHANGE-ME values below.

PythonAnywhere runs the app with its own WSGI server, so gunicorn/Procfile
are not used here. The app must expose the WSGI callable as `application`.
"""

import os
import sys

# --- 1. Point Python at the project checkout ------------------------------
# CHANGE-ME: replace <username> with your PythonAnywhere username.
PROJECT_DIR = '/home/<username>/FlaskApp'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# --- 2. Configuration via environment -------------------------------------
# FLASK_ENV=production makes flaskblog skip loading a local .env file, so we
# set everything the app reads at import time right here.
os.environ.setdefault('FLASK_ENV', 'production')

# CHANGE-ME: any long random string (used to sign sessions/login cookies).
os.environ.setdefault('SECRET_KEY', 'replace-with-a-long-random-string')

# CHANGE-ME: absolute path (note the FOUR slashes) to the uploaded SQLite DB.
os.environ.setdefault(
    'SQLALCHEMY_DATABASE_URI',
    'sqlite:////home/<username>/FlaskApp/instance/posts.db',
)

# GOOGLE_MAPS_API_KEY is intentionally left unset — the app runs fine without
# it (no paid Maps calls); PLUTO ships its own coordinates.

# --- 3. Expose the WSGI application ----------------------------------------
from flaskblog import app as application  # noqa: E402
