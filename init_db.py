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

        # Create all tables that don't exist
        db.create_all()
        print("  -> Checked and created any missing tables")

        # Create admin user only if users table is empty
        if 'users' not in existing_tables or User.query.count() == 0:
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
        else:
            print("  -> Admin user already exists")
        
        # Verify final state
        final_tables = inspect(db.engine).get_table_names()
        print(f"  -> Final database tables: {final_tables}")
        print(f"==> Database initialization completed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1) 