#!/usr/bin/env bash
# Exit on error
set -e

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Install dependencies
echo "==> Installing dependencies..."
pip install -r requirements.txt

# Create database initialization script
cat > init_db.py << 'EOF'
import os, sys, time
from sqlalchemy import text, inspect, MetaData
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db
from models import User, Player, Course, Birdie, HistoricalTotal
from werkzeug.security import generate_password_hash

with app.app_context():
    try:
        print(f"  -> Database URL: {db.engine.url}")
        print("  -> Testing database connection...")
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("  -> Database connection successful")

        # Drop and recreate schema
        print("  -> Setting up schema...")
        with db.engine.connect() as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
            conn.execute(text('CREATE SCHEMA public'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
            conn.execute(text('COMMIT'))

        # Create tables
        print("  -> Creating tables...")
        with db.engine.begin() as conn:
            # Create users table first
            conn.execute(text("""
                CREATE TABLE public.users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    password_hash VARCHAR(256),
                    is_admin BOOLEAN DEFAULT false
                )
            """))
            
            # Create admin user
            password_hash = generate_password_hash('ign')
            conn.execute(text("""
                INSERT INTO public.users (username, password_hash, is_admin)
                VALUES ('mawdisho', :password_hash, true)
            """), {'password_hash': password_hash})
            
            # Create other tables
            conn.execute(text("""
                CREATE TABLE public.player (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    has_trophy BOOLEAN DEFAULT false,
                    permanent_emojis VARCHAR(255)
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE public.course (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE public.birdie (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES public.player(id),
                    course_id INTEGER REFERENCES public.course(id),
                    hole_number INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    date DATE NOT NULL,
                    is_eagle BOOLEAN DEFAULT false
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE public.historical_total (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES public.player(id),
                    year INTEGER NOT NULL,
                    birdies INTEGER NOT NULL DEFAULT 0,
                    eagles INTEGER NOT NULL DEFAULT 0,
                    has_trophy BOOLEAN DEFAULT false
                )
            """))

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
        tables = inspector.get_table_names()
        print(f"    - Found tables: {tables}")
        
        for table in ['users', 'player', 'course', 'birdie', 'historical_total']:
            if table not in tables:
                raise Exception(f"Table {table} was not created successfully")
            columns = [c['name'] for c in inspector.get_columns(table)]
            print(f"    - Verified table {table}:")
            print(f"      Columns: {columns}")

        # Verify admin user
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM users WHERE username = 'mawdisho'")).first()
            if result:
                print("  -> Admin user verified successfully")
            else:
                raise Exception("Admin user was not created successfully")

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

# Verify final state
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
        fks = inspector.get_foreign_keys(table)
        print(f'Table {table}:')
        print(f'  Columns: {columns}')
        if fks:
            print(f'  Foreign keys: {[fk[\"referred_table\"] for fk in fks]}')
    
    # Verify tables exist and are accessible
    from models import User, Player, Course, Birdie, HistoricalTotal
    for model in [User, Player, Course, Birdie, HistoricalTotal]:
        try:
            count = model.query.count()
            print(f'{model.__name__} table is accessible (count: {count})')
        except Exception as e:
            print(f'Error accessing {model.__name__} table: {e}')
            raise
"

# Clean up
rm -f init_db.py 