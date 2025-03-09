#!/bin/bash
# Exit on error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Add the current directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Set the FLASK_APP environment variable
export FLASK_APP=wsgi.py

# Initialize database migrations if they don't exist
if [ ! -d "migrations" ]; then
    flask db init
fi

# Create and upgrade database using proper application context
python - << EOF
from __init__ import create_app
from models import db

app = create_app()
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")
EOF

# Run database migrations
flask db migrate -m "Automatic migration"
flask db upgrade

# Print debug information
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Flask app: $FLASK_APP" 