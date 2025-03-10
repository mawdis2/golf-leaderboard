import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app
from extensions import db
from models import User, Player, Course, Birdie, HistoricalTotal
from sqlalchemy import inspect

def table_exists(table_name, inspector):
    return table_name in inspector.get_table_names()

with app.app_context():
    try:
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"  -> Found existing tables: {existing_tables}")

        # Drop and recreate all tables
        print("  -> Creating all tables...")
        db.drop_all()  # This will drop all tables
        db.create_all()  # This will create all tables fresh
        print("  -> Tables created successfully")

        # Create admin user
        print("  -> Creating admin user...")
        admin = User(username='mawdisho', is_admin=True)
        admin.set_password('ign')
        db.session.add(admin)
        try:
            db.session.commit()
            print("  -> Admin user created successfully")
        except Exception as e:
            db.session.rollback()
            print(f"  -> Error creating admin user: {e}")
        
        # Verify final state
        final_tables = inspect(db.engine).get_table_names()
        print(f"  -> Final database tables: {final_tables}")
        if 'users' in final_tables:
            user_count = User.query.count()
            print(f"  -> Found {user_count} users in the database")
        
        print(f"==> Database initialization completed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1) 