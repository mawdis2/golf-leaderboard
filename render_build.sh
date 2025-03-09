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
from sqlalchemy import text
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db
from models import Player, Course, Birdie, HistoricalTotal

def verify_table_exists(table_name):
    with db.engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table)"
        ), {"table": table_name})
        return result.scalar()

with app.app_context():
    try:
        print("  -> Starting transaction...")
        db.session.begin_nested()
        
        print("  -> Dropping schema...")
        db.session.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
        db.session.execute(text('CREATE SCHEMA public'))
        
        print("  -> Setting permissions...")
        db.session.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
        db.session.execute(text('GRANT ALL ON SCHEMA public TO public'))
        
        print("  -> Creating tables...")
        # Create tables with explicit column definitions
        db.session.execute(text("""
            CREATE TABLE player (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                permanent_emojis TEXT,
                has_trophy BOOLEAN DEFAULT FALSE
            )
        """))
        
        db.session.execute(text("""
            CREATE TABLE course (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            )
        """))
        
        db.session.execute(text("""
            CREATE TABLE birdie (
                id SERIAL PRIMARY KEY,
                player_id INTEGER REFERENCES player(id),
                course_id INTEGER REFERENCES course(id),
                hole_number INTEGER NOT NULL,
                year INTEGER,
                date DATE,
                is_eagle BOOLEAN DEFAULT FALSE
            )
        """))
        
        db.session.execute(text("""
            CREATE TABLE historical_total (
                id SERIAL PRIMARY KEY,
                player_id INTEGER REFERENCES player(id),
                year INTEGER NOT NULL,
                birdies INTEGER DEFAULT 0,
                eagles INTEGER DEFAULT 0,
                has_trophy BOOLEAN DEFAULT FALSE
            )
        """))
        
        print("  -> Setting table permissions...")
        db.session.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres'))
        db.session.execute(text('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres'))
        db.session.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO public'))
        db.session.execute(text('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO public'))
        
        print("  -> Committing transaction...")
        db.session.commit()
        
        # Verify tables were created
        tables = ['player', 'course', 'birdie', 'historical_total']
        for table in tables:
            if not verify_table_exists(table):
                raise Exception(f"Table {table} was not created successfully")
            print(f"  -> Verified table {table} exists")
            
        print(f"==> Database initialized successfully in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        db.session.rollback()
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
flask db migrate -m "Initial migration"
flask db upgrade

# Clean up
rm -f init_db.py 