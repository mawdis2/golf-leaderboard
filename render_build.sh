#!/usr/bin/env bash
# Exit on error
set -e

# Upgrade pip without warnings
python -m pip install --upgrade pip --quiet

# Install Python dependencies with optimizations
python -m pip install --no-cache-dir -r requirements.txt

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production

# Create a Python script for database initialization
cat > init_db.py << 'EOF'
from app import db
from flask import current_app

with current_app.app_context():
    # Drop and recreate schema in one go
    db.session.execute('DROP SCHEMA IF EXISTS public CASCADE')
    db.session.execute('CREATE SCHEMA public')
    db.session.execute('GRANT ALL ON SCHEMA public TO postgres')
    db.session.execute('GRANT ALL ON SCHEMA public TO public')
    db.session.commit()
    
    # Initialize database
    db.create_all()
    db.session.commit()
EOF

# Initialize database with error handling
if ! python init_db.py; then
    echo "Database initialization failed"
    exit 1
fi

# Run migrations with minimal output and error handling
if ! flask db upgrade --sql > /dev/null 2>&1; then
    echo "Database migration failed"
    exit 1
fi

# Clean up
rm -f init_db.py

# Start the application with optimized settings
exec gunicorn app:app --workers=2 --threads=4 --worker-class=gthread --timeout 120 