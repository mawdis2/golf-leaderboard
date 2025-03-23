"""
Migration script to add year column to tournament table.
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_year_column():
    with app.app_context():
        print("Adding year column to tournament table...")
        try:
            # Add year column
            db.session.execute(text("ALTER TABLE tournament ADD COLUMN year INTEGER NOT NULL DEFAULT EXTRACT(YEAR FROM date)"))
            db.session.commit()
            print("Year column added successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding year column: {e}")

if __name__ == "__main__":
    add_year_column() 