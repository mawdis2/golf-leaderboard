import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db
from models import User
from sqlalchemy import inspect

def table_exists(table_name, inspector):
    return table_name in inspector.get_table_names()

with app.app_context():
    try:
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"  -> Found existing tables: {existing_tables}")

        # Only create tables that don't exist
        db.create_all()
        print("  -> Checked and created any missing tables")

        # Create admin user only if user table is empty
        if table_exists('user', inspector):
            user_count = User.query.count()
            if user_count == 0:
                print("  -> Creating admin user...")
                admin = User(username='mawdisho', is_admin=True)
                admin.set_password('ign')
                db.session.add(admin)
                db.session.commit()
                print("  -> Admin user created")
            else:
                print(f"  -> Found {user_count} existing users, skipping admin creation")
        
        # Verify final state
        final_tables = inspect(db.engine).get_table_names()
        print(f"  -> Final database tables: {final_tables}")
        print(f"==> Database initialization completed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1) 