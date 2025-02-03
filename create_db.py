# create_db.py
from models import db, User, Player, Birdie, Course
from create_app import create_app

def create_database():
    app = create_app()
    with app.app_context():
        db.drop_all()  # Ensure any existing tables are dropped
        db.create_all()  # Create all tables
        print("Database and tables created successfully.")

if __name__ == "__main__":
    create_database()