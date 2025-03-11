import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import create_app
from extensions import db
from models import User, Player, Course, Birdie, HistoricalTotal, Eagle
from sqlalchemy import inspect, text
from flask import Flask
from werkzeug.security import generate_password_hash
from datetime import datetime

def verify_table_exists(table_name, inspector):
    tables = inspector.get_table_names()
    exists = table_name in tables
    print(f"  -> Checking table '{table_name}': {'EXISTS' if exists else 'MISSING'}")
    return exists

def verify_table_columns(table_name, inspector):
    columns = inspector.get_columns(table_name)
    print(f"  -> Table '{table_name}' columns:")
    for column in columns:
        print(f"     - {column['name']}: {column['type']}")

app = create_app()

with app.app_context():
    try:
        print("==> Starting database setup...")
        
        # Get database URL (with password masked)
        db_url = str(db.engine.url)
        if '@' in db_url:
            db_url = db_url.split('@')[1]
        print(f"  -> Using database: {db_url}")
        
        # Create tables if they don't exist
        print("  -> Creating tables if they don't exist...")
        db.create_all()
        
        # Verify tables were created
        inspector = inspect(db.engine)
        tables_after = inspector.get_table_names()
        print(f"  -> Tables after creation: {tables_after}")
        
        # Verify all required tables
        required_tables = ['users', 'player', 'course', 'birdie', 'historical_total', 'eagle']
        for table in required_tables:
            if verify_table_exists(table, inspector):
                verify_table_columns(table, inspector)
            else:
                print(f"  -> ERROR: Required table '{table}' is missing!")
                raise Exception(f"Required table '{table}' was not created")
        
        # Check if admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("  -> Creating admin user...")
            admin_user = User(
                username='admin',
                is_admin=True
            )
            admin_user.set_password('shotgun')  # You can change this password
            db.session.add(admin_user)
            db.session.commit()
            print("  -> Admin user created successfully")
        else:
            print("  -> Admin user already exists")
        
        print(f"\n==> Database initialization completed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    with app.app_context():
        init_db()