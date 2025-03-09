#!/bin/bash
# Exit on error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Set the FLASK_APP environment variable
export FLASK_APP=app.py

# Run database migrations
python -c "from app import db; db.create_all()"
FLASK_APP=app.py flask db upgrade 