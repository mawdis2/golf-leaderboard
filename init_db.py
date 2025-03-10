import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import create_app
from extensions import db
from models import User, Player, Course, Birdie, HistoricalTotal, Eagle
from sqlalchemy import inspect, text

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
        
        # Drop all existing tables
        print("  -> Dropping existing tables...")
        db.drop_all()
        
        # Create all tables fresh
        print("  -> Creating all tables...")
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
        
        # Create admin user
        print("\n==> Creating admin user...")
        admin = User(username='mawdisho', is_admin=True)
        admin.set_password('ign')
        db.session.add(admin)
        
        try:
            db.session.commit()
            print("  -> Admin user created successfully")
            
            # Verify admin user was created
            admin_user = User.query.filter_by(username='mawdisho').first()
            if admin_user:
                print(f"  -> Verified admin user exists:")
                print(f"     - Username: {admin_user.username}")
                print(f"     - ID: {admin_user.id}")
                print(f"     - Admin: {admin_user.is_admin}")
            else:
                print("  -> WARNING: Admin user not found after creation!")
                raise Exception("Failed to create admin user")
                
        except Exception as e:
            db.session.rollback()
            print(f"  -> Error creating admin user: {e}")
            raise
        
        print(f"\n==> Database initialization completed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1) 