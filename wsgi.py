"""
WSGI Entry Point for Production Deployment
Apache/Nginx + mod_wsgi/Gunicorn
"""

import sys
import os

# Add project directory to Python path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env
from dotenv import load_dotenv
env_path = os.path.join(project_home, '.env')
load_dotenv(env_path)

# Create Flask application
from app import create_app
application = create_app()

if __name__ == '__main__':
    application.run()
