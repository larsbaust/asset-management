# Asset Management System

A Flask-based asset management system for tracking inventory, managing assets, and conducting inventory checks.

## Deployment to PythonAnywhere

1. Go to [PythonAnywhere](https://www.pythonanywhere.com/) and create a free account

2. Once logged in:
   - Click on "Web" in the top navigation
   - Click "Add a new web app"
   - Choose "Manual configuration"
   - Choose Python 3.9

3. In the "Code" section:
   - Go to "Files"
   - Upload all project files or use Git to clone the repository

4. In the "Web" section, configure:
   - Source code: /home/yourusername/asset-management
   - Working directory: /home/yourusername/asset-management
   - WSGI configuration file: Update the path in the WSGI file to point to your project's wsgi.py

5. Set up your virtual environment:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.9 myenv
   pip install -r requirements.txt
   ```

6. Configure environment variables:
   - Go to the "Files" section
   - Create a .env file in your project directory
   - Add your environment variables:
     ```
     FLASK_APP=app
     FLASK_ENV=production
     SECRET_KEY=your-secret-key-here
     DATABASE_URL=sqlite:///app.db
     ```

7. Create the database:
   ```bash
   flask db upgrade
   ```

8. Reload your web app from the "Web" tab

Your application should now be live at yourusername.pythonanywhere.com

## Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy .env.example to .env
   - Update the values as needed

4. Initialize the database:
   ```bash
   flask db upgrade
   ```

5. Run the application:
   ```bash
   flask run
   ```

## Features

- Asset Management
- Inventory Control
- Image Upload Support
- Multiple Assignments
- Manufacturer & Supplier Management
- Inventory Reports
- Search Functionality
