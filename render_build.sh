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
from app import create_app, db

app = create_app()
with app.app_context():
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
EOF

# Initialize database with error handling
echo "Starting database initialization..."
if ! python init_db.py; then
    echo "Database initialization failed"
    exit 1
fi

# Run migrations with minimal output and error handling
echo "Running database migrations..."
if ! flask db upgrade; then
    echo "Database migration failed"
    exit 1
fi

# Clean up
rm -f init_db.py

echo "Starting Gunicorn server..."
# Start the application with optimized settings
exec gunicorn app:app --workers=2 --threads=4 --worker-class=gthread --timeout 120 