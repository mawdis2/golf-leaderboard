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
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Create a Python script for database initialization
cat > init_db.py << 'EOF'
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

with app.app_context():
    try:
        print("Dropping existing schema...")
        db.session.execute('DROP SCHEMA IF EXISTS public CASCADE')
        print("Creating new schema...")
        db.session.execute('CREATE SCHEMA public')
        db.session.execute('GRANT ALL ON SCHEMA public TO postgres')
        db.session.execute('GRANT ALL ON SCHEMA public TO public')
        db.session.commit()
        
        print("Creating database tables...")
        db.create_all()
        db.session.commit()
        print("Database initialization completed successfully!")
    except Exception as e:
        print(f"Error during database initialization: {str(e)}")
        raise
EOF

# Initialize database with error handling
echo "Starting database initialization..."
if ! python init_db.py; then
    echo "Database initialization failed"
    exit 1
fi

# Create migrations directory if it doesn't exist
mkdir -p migrations

# Initialize migrations if not already initialized
if [ ! -f "migrations/alembic.ini" ]; then
    echo "Initializing migrations..."
    flask db init
fi

# Run migrations with error handling
echo "Running database migrations..."
if ! PYTHONPATH=/opt/render/project/src flask db upgrade; then
    echo "Database migration failed"
    exit 1
fi

# Clean up
rm -f init_db.py

echo "Starting Gunicorn server..."
# Start the application with optimized settings
exec gunicorn "app:app" --workers=2 --threads=4 --worker-class=gthread --timeout 120 