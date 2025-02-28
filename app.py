from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

app = Flask(__name__)

# Secret key configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Use PostgreSQL in production
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Use SQLite in development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///birdie_tracker.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Import routes after app is created
from routes import *

if __name__ == '__main__':
    app.run(debug=True)