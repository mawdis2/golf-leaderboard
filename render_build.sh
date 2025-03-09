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

app = create_app()
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
EOF

# Run the database initialization script
python init_db.py

# Initialize database migrations if they don't exist
if [ ! -d "migrations" ]; then
    flask db init
fi

# Run database migrations
flask db migrate -m "Automatic migration"
flask db upgrade

# Clean up
rm init_db.py

# Print debug information
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Flask app: $FLASK_APP" 