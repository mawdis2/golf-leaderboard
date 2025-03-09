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
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db
from models import Player, Course, Birdie, HistoricalTotal

with app.app_context():
    try:
        print("  -> Dropping schema...")
        db.session.execute('DROP SCHEMA IF EXISTS public CASCADE')
        print("  -> Creating schema...")
        db.session.execute('CREATE SCHEMA public')
        db.session.execute('GRANT ALL ON SCHEMA public TO postgres')
        db.session.execute('GRANT ALL ON SCHEMA public TO public')
        db.session.commit()
        
        print("  -> Creating tables...")
        # Create tables with explicit column definitions
        db.session.execute("""
            CREATE TABLE player (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                permanent_emojis TEXT,
                has_trophy BOOLEAN DEFAULT FALSE
            )
        """)
        
        db.session.execute("""
            CREATE TABLE course (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            )
        """)
        
        db.session.execute("""
            CREATE TABLE birdie (
                id SERIAL PRIMARY KEY,
                player_id INTEGER REFERENCES player(id),
                course_id INTEGER REFERENCES course(id),
                hole_number INTEGER NOT NULL,
                year INTEGER,
                date DATE,
                is_eagle BOOLEAN DEFAULT FALSE
            )
        """)
        
        db.session.execute("""
            CREATE TABLE historical_total (
                id SERIAL PRIMARY KEY,
                player_id INTEGER REFERENCES player(id),
                year INTEGER NOT NULL,
                birdies INTEGER DEFAULT 0,
                eagles INTEGER DEFAULT 0,
                has_trophy BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Ensure proper permissions
        db.session.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres')
        db.session.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres')
        db.session.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO public')
        db.session.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO public')
        
        db.session.commit()
        print(f"==> Database initialized successfully in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"==> Database initialization error: {e}")
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