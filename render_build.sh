#!/usr/bin/env bash
# Exit on error
set -e

echo "==> Starting deployment process..."

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src
export PIP_NO_CACHE_DIR=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

# Install dependencies efficiently
echo "==> Installing dependencies..."
python -m pip install --no-cache-dir --quiet -r requirements.txt

# Database initialization script
cat > init_db.py << 'EOF'
import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db

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
        db.create_all()
        db.session.commit()
        print(f"==> Database initialized successfully in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1)
EOF

# Initialize database with timeout
echo "==> Running database initialization..."
timeout 60s python init_db.py || { echo "Database initialization timed out after 60s"; exit 1; }

# Handle migrations with timeout
echo "==> Setting up migrations..."
if [ ! -d "migrations" ]; then
    timeout 30s flask db init || { echo "Migration initialization timed out after 30s"; exit 1; }
fi

echo "==> Running migrations..."
timeout 30s flask db upgrade || { echo "Migration upgrade timed out after 30s"; exit 1; }

# Clean up
rm -f init_db.py

# Start server directly
echo "==> Starting server..."
gunicorn \
    --bind=0.0.0.0:10000 \
    --worker-class=sync \
    --workers=1 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=- \
    app:app 