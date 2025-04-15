import sys
import os

path = '/home/frittenbude/asset-management'
if path not in sys.path:
    sys.path.append(path)

from dotenv import load_dotenv
load_dotenv(os.path.join(path, '.env'))

from app import create_app
application = create_app()

if __name__ == '__main__':
    application.run()
