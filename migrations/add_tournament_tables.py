"""
Migration script to add tournament tables to the database.
Run this script after deploying the code changes.
"""

import sys
import os

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import Tournament, Team, TeamMember, TournamentResult

app = create_app()

def upgrade():
    with app.app_context():
        # Create the new tables
        db.create_all()
        print("Tournament tables created successfully!")

if __name__ == "__main__":
    upgrade() 