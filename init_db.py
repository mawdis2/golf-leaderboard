import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db

with app.app_context():
    try:
        print("  -> Creating tables if they don't exist...")
        db.create_all()
        db.session.commit()
        print(f"==> Database initialized successfully in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1) 