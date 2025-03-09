#!/bin/bash
# Exit on error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Add the current directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Set the FLASK_APP environment variable
export FLASK_APP=wsgi.py

# Create a temporary Python script for database initialization
cat > init_db.py << 'EOF'
from __init__ import create_app
from models import db, User, Player, Birdie, Course, HistoricalTotal, Eagle
import sqlalchemy as sa
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # Drop tables in the correct order to handle dependencies
        db.session.execute(text("""
            -- First drop dependent tables
            DROP TABLE IF EXISTS "birdie" CASCADE;
            DROP TABLE IF EXISTS "eagle" CASCADE;
            DROP TABLE IF EXISTS "historical_total" CASCADE;
            
            -- Then drop the tables they depend on
            DROP TABLE IF EXISTS "player" CASCADE;
            DROP TABLE IF EXISTS "course" CASCADE;
            DROP TABLE IF EXISTS "user" CASCADE;
            
            -- Finally drop the migrations table
            DROP TABLE IF EXISTS "alembic_version" CASCADE;
        """))
        db.session.commit()
        
        # Create all tables fresh
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        db.session.rollback()
        raise
EOF

# Run the database initialization script
python init_db.py

# Remove existing migrations directory if it exists
rm -rf migrations

# Initialize fresh migrations
flask db init

# Create initial migration
flask db migrate -m "Initial migration"

# Upgrade database
FLASK_APP=wsgi.py flask db upgrade

# Clean up
rm init_db.py

# Print debug information
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Flask app: $FLASK_APP" 