#!/bin/bash
# Exit on error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python -c "from app import db; db.create_all()"
flask db upgrade 