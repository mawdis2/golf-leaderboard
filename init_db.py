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
from sqlalchemy.exc import OperationalError, ProgrammingError

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
        
        # Test database connection
        print("  -> Testing database connection...")
        try:
            db.engine.connect()
            print("  -> Database connection successful")
        except OperationalError as e:
            print(f"  -> Database connection failed: {e}")
            sys.exit(1)
        
        # Create tables if they don't exist
        print("  -> Creating tables if they don't exist...")
        db.create_all()
        
        # Check if trophy_count column exists in historical_total table
        # If not, add it
        print("  -> Checking for trophy_count column...")
        try:
            db.session.execute(text("SELECT trophy_count FROM historical_total LIMIT 1"))
            print("  -> trophy_count column already exists")
        except (OperationalError, ProgrammingError):
            print("  -> Adding trophy_count column to historical_total table...")
            try:
                db.session.execute(text("ALTER TABLE historical_total ADD COLUMN trophy_count INTEGER DEFAULT 0"))
                db.session.commit()
                print("  -> trophy_count column added successfully")
            except Exception as e:
                db.session.rollback()
                print(f"  -> Error adding trophy_count column: {e}")
        
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

def verify_db():
    print("==> Verifying final database state...")
    app = create_app()
    
    with app.app_context():
        tables = db.engine.table_names()
        print(f"Tables in the database: {tables}")
        
        # Check if Birdie table exists
        if 'birdie' in tables:
            result = db.session.execute(text("SELECT COUNT(*) FROM birdie"))
            count = result.scalar()
            print(f"The Birdie table has {count} records.")
        else:
            print("The Birdie table does not exist in the database.")

if __name__ == '__main__':
    with app.app_context():
        init_db()
        verify_db()