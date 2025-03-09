#!/usr/bin/env bash
# Exit on error
set -e

echo "==> Installing dependencies..."
python -m pip install --no-cache-dir -r requirements.txt

echo "==> Initializing database..."
python init_db.py

echo "==> Setting up migrations..."
if [ ! -d "migrations" ]; then
    flask db init
fi

echo "==> Running migrations..."
flask db upgrade 