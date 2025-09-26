import sys
import os

# Add the project directory to the Python path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# CRITICAL: Load environment variables from .env file BEFORE creating the app
from dotenv import load_dotenv
dotenv_path = os.path.join(project_home, '.env')
load_dotenv(dotenv_path)

# Import and create the Flask application instance
from zetsu import create_app
application = create_app(os.getenv('FLASK_ENV', 'production'))
