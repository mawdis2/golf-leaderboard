from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

app = Flask(__name__)

# Secret key configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Handle potential "postgres://" format in the URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Use SQLite in development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///birdie_tracker.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Import all models to ensure they're registered before creating tables
from .models import User, Player, Birdie, Course, HistoricalTotal, Eagle

# Import routes after app is created
from .routes import bp
app.register_blueprint(bp)

@app.route('/')
def index():
    return redirect(url_for('main.leaderboard'))

# Add these lines to create tables
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == '__main__':
    app.run(debug=True)