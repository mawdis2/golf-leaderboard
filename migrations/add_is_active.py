import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_is_active():
    with app.app_context():
        print("Adding is_active column to tournament table...")
        try:
            db.session.execute(text("ALTER TABLE tournament ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
            db.session.commit()
            print("Successfully added is_active column")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding is_active column: {e}")

if __name__ == "__main__":
    add_is_active() 