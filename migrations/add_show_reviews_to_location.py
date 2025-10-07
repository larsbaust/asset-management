"""
Add show_reviews field to Location model

This migration adds a new Boolean field 'show_reviews' to the Location table.
Default value is True, meaning reviews/description slider is shown by default.

To apply this migration, run:
    python migrations/add_show_reviews_to_location.py
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Location

def migrate():
    """Add show_reviews column to location table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('location')]
            
            if 'show_reviews' in columns:
                print('[OK] Column "show_reviews" already exists. Nothing to do.')
                return
            
            # Add the column using raw SQL
            print('[INFO] Adding "show_reviews" column to location table...')
            db.session.execute(db.text(
                'ALTER TABLE location ADD COLUMN show_reviews BOOLEAN DEFAULT 1'
            ))
            db.session.commit()
            
            print('[SUCCESS] Successfully added "show_reviews" column!')
            print('          All existing locations will have show_reviews=True by default.')
            
        except Exception as e:
            print(f'[ERROR] Error during migration: {e}')
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate()
