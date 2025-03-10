import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db
from sqlalchemy import inspect

with app.app_context():
    try:
        # Check if tables exist
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if not existing_tables:
            print("  -> No tables found. Creating tables...")
            db.create_all()
            print("  -> Tables created successfully!")
        else:
            print(f"  -> Found existing tables: {existing_tables}")
            print("  -> Database already initialized, skipping creation.")
        
        print(f"==> Database initialization completed in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1) 