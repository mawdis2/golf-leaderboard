#!/bin/bash
# Exit on error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Add the current directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Set the FLASK_APP environment variable
export FLASK_APP=app.py

# Initialize database migrations if they don't exist
if [ ! -d "migrations" ]; then
    flask db init
fi

# Create and upgrade database
python -c "from app import db; db.create_all()"
flask db migrate -m "Automatic migration"
flask db upgrade

# Print debug information
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Flask app: $FLASK_APP" 