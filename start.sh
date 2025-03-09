#!/usr/bin/env bash

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Start Gunicorn with proper configuration
exec gunicorn \
    --bind=0.0.0.0:$PORT \
    --workers=1 \
    --threads=4 \
    --timeout=30 \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=debug \
    --capture-output \
    app:app 