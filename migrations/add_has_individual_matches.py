import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_has_individual_matches():
    with app.app_context():
        print("Adding has_individual_matches column to tournament table...")
        try:
            db.session.execute(text("ALTER TABLE tournament ADD COLUMN has_individual_matches BOOLEAN DEFAULT FALSE"))
            db.session.commit()
            print("Successfully added has_individual_matches column")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding has_individual_matches column: {e}")

if __name__ == "__main__":
    add_has_individual_matches() 