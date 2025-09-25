"""
WSGI configuration for PythonAnywhere deployment.

This file is used by PythonAnywhere to serve your Flask application.
Update the path in your PythonAnywhere web configuration to point to this file.
"""

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/zetsuserv'  # UPDATE THIS with your PythonAnywhere username
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable for Flask
os.environ['FLASK_ENV'] = 'production'

# Import your application
from app import application

# Ensure the application context is available
if __name__ == "__main__":
    application.run()