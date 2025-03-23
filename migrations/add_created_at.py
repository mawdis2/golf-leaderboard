import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_created_at():
    with app.app_context():
        print("Adding created_at column to tournament table...")
        try:
            db.session.execute(text("ALTER TABLE tournament ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            db.session.commit()
            print("Successfully added created_at column")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding created_at column: {e}")

if __name__ == "__main__":
    add_created_at() 