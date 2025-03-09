#!/usr/bin/env bash
export FLASK_APP=app
export FLASK_ENV=production

exec gunicorn \
    --bind=0.0.0.0:$PORT \
    --workers=1 \
    --threads=4 \
    --timeout=30 \
    --access-logfile=- \
    --error-logfile=- \
    app:app 