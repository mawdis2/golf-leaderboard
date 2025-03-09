#!/usr/bin/env bash
# Exit on error and handle interrupts
set -e
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src
export PIP_NO_CACHE_DIR=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

# Install dependencies efficiently
echo "Installing dependencies..."
python -m pip install --no-cache-dir --quiet -r requirements.txt

# Database initialization script
cat > init_db.py << 'EOF'
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

with app.app_context():
    try:
        db.session.execute('DROP SCHEMA IF EXISTS public CASCADE')
        db.session.execute('CREATE SCHEMA public')
        db.session.execute('GRANT ALL ON SCHEMA public TO postgres')
        db.session.execute('GRANT ALL ON SCHEMA public TO public')
        db.session.commit()
        db.create_all()
        db.session.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        sys.exit(1)
EOF

# Initialize database
echo "Initializing database..."
python init_db.py

# Handle migrations
echo "Setting up migrations..."
if [ ! -d "migrations" ]; then
    flask db init
fi

echo "Running migrations..."
flask db upgrade

# Clean up
rm -f init_db.py

# Start Gunicorn with proper signal handling
echo "Starting Gunicorn server..."
exec gunicorn "app:app" \
    --bind=0.0.0.0:10000 \
    --workers=2 \
    --threads=4 \
    --worker-class=gthread \
    --timeout=30 \
    --graceful-timeout=10 \
    --keep-alive=5 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=- \
    --capture-output 