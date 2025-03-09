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
        # Drop and recreate the schema to handle all dependencies at once
        db.session.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
        db.session.execute(text('CREATE SCHEMA public'))
        db.session.execute(text('GRANT ALL ON SCHEMA public TO public'))
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
flask db upgrade

# Clean up
rm init_db.py

# Print debug information
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Flask app: $FLASK_APP" 