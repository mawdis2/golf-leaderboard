#!/usr/bin/env bash
# Exit on error
set -e

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Install dependencies
echo "==> Installing dependencies..."
python -m pip install --no-cache-dir -r requirements.txt

# Create database initialization script
cat > init_db.py << 'EOF'
import os, sys, time
from sqlalchemy import text, inspect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db
from models import Player, Course, Birdie, HistoricalTotal

def verify_table_exists(table_name):
    with db.engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :table)"
        ), {"table": table_name})
        return result.scalar()

with app.app_context():
    try:
        print(f"  -> Database URL: {db.engine.url}")
        print("  -> Testing database connection...")
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("  -> Database connection successful")

        # First transaction: Schema setup
        print("  -> Setting up schema...")
        with db.engine.connect() as conn:
            conn.execute(text('COMMIT'))  # Close any existing transaction
            conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
            conn.execute(text('CREATE SCHEMA public'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
            conn.execute(text('COMMIT'))
        
        print("  -> Verifying models...")
        # Explicitly register models with SQLAlchemy
        models = [Player, Course, Birdie, HistoricalTotal]
        for model in models:
            print(f"    - Registering model: {model.__name__}")
            if not hasattr(model, '__table__'):
                raise Exception(f"Model {model.__name__} has no __table__ attribute")
            print(f"      Table name: {model.__table__.name}")
            print(f"      Columns: {', '.join(c.name for c in model.__table__.columns)}")
        
        print("  -> Creating tables using SQLAlchemy...")
        # Create tables using both methods to ensure success
        db.create_all()
        for model in models:
            if not model.__table__.exists(db.engine):
                print(f"    - Table {model.__table__.name} not created by create_all(), trying direct creation...")
                model.__table__.create(db.engine)
        
        # Set permissions
        print("  -> Setting permissions...")
        with db.engine.begin() as conn:
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO public'))
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO public'))
        
        # Verify tables
        print("  -> Verifying tables...")
        inspector = inspect(db.engine)
        tables = ['player', 'course', 'birdie', 'historical_total']
        existing_tables = inspector.get_table_names()
        print(f"    - Found tables: {existing_tables}")
        
        for table in tables:
            if not table in existing_tables:
                # Try to diagnose why the table is missing
                print(f"    - Diagnosing missing table {table}...")
                with db.engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT pg_get_viewdef(format('%I.%I', schemaname, viewname), true) "
                        "FROM pg_views WHERE schemaname = 'public'"
                    ))
                    views = result.fetchall()
                    if views:
                        print(f"      Found views: {views}")
                raise Exception(f"Table {table} was not created successfully")
            columns = [c['name'] for c in inspector.get_columns(table)]
            print(f"    - Verified table {table} exists with columns: {columns}")
            
        print(f"==> Database initialized successfully in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        import traceback
        print("  -> Full error details:")
        traceback.print_exc()
        sys.exit(1)
EOF

# Initialize database
echo "==> Initializing database..."
python init_db.py

# Remove existing migrations
echo "==> Cleaning up old migrations..."
rm -rf migrations

# Initialize fresh migrations
echo "==> Setting up fresh migrations..."
flask db init

# Create initial migration
echo "==> Creating initial migration..."
flask db migrate -m "Initial migration"

# Apply migration
echo "==> Applying migration..."
flask db upgrade

# Verify database state
echo "==> Verifying final database state..."
python -c "
from app import app, db
from sqlalchemy import inspect
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print('Available tables:', tables)
    for table in tables:
        columns = [c['name'] for c in inspector.get_columns(table)]
        print(f'Table {table} columns:', columns)
    if not all(t in tables for t in ['player', 'course', 'birdie', 'historical_total']):
        raise Exception('Missing required tables')
"

# Clean up
rm -f init_db.py 