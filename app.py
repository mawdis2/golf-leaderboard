# app.py
from . import app
from .config import Config
from .extensions import db, migrate, login_manager
from .models import User
from middleware import require_site_password
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

migrate.init_app(app, db)
login_manager.init_app(app)

# Remove the blueprint registration line
# app.register_blueprint(bp)  # This line should be removed

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Use PostgreSQL in production
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Use SQLite in development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///birdie_tracker.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.route('/')
@require_site_password
def index():
    # ... existing code ...

@app.route('/leaderboard')
@require_site_password
def leaderboard():
    # ... existing code ...

if __name__ == '__main__':
    app.run(debug=True)