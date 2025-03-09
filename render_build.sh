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
        
        # Ensure proper permissions on all tables
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

# Handle migrations
echo "==> Setting up migrations..."
if [ ! -d "migrations" ]; then
    flask db init
fi

echo "==> Running migrations..."
flask db upgrade

# Clean up
rm -f init_db.py 