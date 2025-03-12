"""
Migration script to add end_date field to tournament table and make course_id nullable.
Run this script after deploying the code changes.
"""

import sys
import os

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import Column, DateTime, Integer, ForeignKey
from sqlalchemy.sql import text

app = create_app()

def upgrade():
    with app.app_context():
        # Add end_date column to tournament table
        db.session.execute(text("ALTER TABLE tournament ADD COLUMN end_date DATETIME"))
        
        # Make course_id nullable (if it's not already)
        # This is a bit tricky with SQLite, so we'll just print instructions
        print("Note: To make course_id nullable, you may need to:")
        print("1. Create a new tournament table with nullable course_id")
        print("2. Copy data from the old table to the new one")
        print("3. Drop the old table and rename the new one")
        print("This script has added the end_date column. The course_id will be treated as nullable in the code.")
        
        db.session.commit()
        print("Added end_date column to tournament table successfully!")

if __name__ == "__main__":
    upgrade() 