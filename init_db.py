import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import create_app, db
from models import User, Player, Course, Birdie, HistoricalTotal, Eagle
from sqlalchemy import inspect, text

def verify_table_exists(table_name, inspector):
    tables = inspector.get_table_names()
    exists = table_name in tables
    print(f"  -> Checking table '{table_name}': {'EXISTS' if exists else 'MISSING'}")
    return exists

app = create_app()

with app.app_context():
    try:
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"  -> Found existing tables: {existing_tables}")

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
        
        # Verify specific tables
        verify_table_exists('users', inspector)
        verify_table_exists('player', inspector)
        verify_table_exists('course', inspector)
        verify_table_exists('birdie', inspector)
        
        # Create admin user
        print("  -> Creating admin user...")
        admin = User(username='mawdisho', is_admin=True)
        admin.set_password('ign')
        db.session.add(admin)
        
        try:
            db.session.commit()
            print("  -> Admin user created successfully")
            
            # Verify admin user was created
            user_count = User.query.count()
            admin_user = User.query.filter_by(username='mawdisho').first()
            if admin_user:
                print(f"  -> Verified admin user exists: {admin_user.username}")
            else:
                print("  -> WARNING: Admin user not found after creation!")
        except Exception as e:
            db.session.rollback()
            print(f"  -> Error creating admin user: {e}")
        
        print(f"==> Database initialization completed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1) 