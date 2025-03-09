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

# Create health check script
cat > healthcheck.py << 'EOF'
import sys
import socket
import time

def check_port(port, retries=5, delay=1):
    for i in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result == 0:
            print("Server is up!")
            return True
        print(f"Attempt {i+1}/{retries}: Server not ready...")
        time.sleep(delay)
    return False

if not check_port(10000):
    print("Server failed to start")
    sys.exit(1)
EOF

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

# Clean up database script
rm -f init_db.py

# Start server in background and verify it's running
echo "==> Starting server..."
gunicorn \
    --bind=0.0.0.0:10000 \
    --worker-class=gthread \
    --workers=1 \
    --threads=4 \
    --timeout=30 \
    --graceful-timeout=10 \
    --keep-alive=5 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=- \
    --preload \
    --forwarded-allow-ips="*" \
    app:app &

# Wait for server to start
echo "==> Checking server health..."
timeout 30s python healthcheck.py || { echo "Server failed to start within 30s"; exit 1; }

# Keep the script running but allow for proper shutdown
wait $! 