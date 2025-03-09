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
        # Drop all tables with CASCADE
        db.session.execute(text('DROP SCHEMA public CASCADE;'))
        db.session.execute(text('CREATE SCHEMA public;'))
        db.session.commit()
        
        # Create all tables fresh
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        db.session.rollback()
EOF

# Run the database initialization script
python init_db.py

# Initialize database migrations if they don't exist
if [ ! -d "migrations" ]; then
    flask db init
fi

# Create a fresh migration
rm -f migrations/versions/*
flask db migrate -m "Initial migration"
flask db upgrade

# Clean up
rm init_db.py

# Print debug information
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Flask app: $FLASK_APP" 