"""
Migration script to add tournament tables to the database.
Run this script after deploying the code changes.
"""

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