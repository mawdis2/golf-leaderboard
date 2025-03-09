#!/bin/bash
# Exit on error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Add the current directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Set the FLASK_APP environment variable
export FLASK_APP=app.py

# Run database migrations
python -c "from app import db; db.create_all()"
FLASK_APP=app.py flask db upgrade 