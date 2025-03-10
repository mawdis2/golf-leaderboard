from flask import Flask, redirect, url_for
import os
from extensions import init_extensions, db, login_manager

def create_app():
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
    init_extensions(app)

    with app.app_context():
        # Import models here to avoid circular imports
        from models import User, Player, Birdie, Course, HistoricalTotal, Eagle
        
        # Create all database tables
        db.create_all()
        
        # Register blueprints
        from routes import bp
        app.register_blueprint(bp)

    return app

app = create_app()

@app.route('/')
def index():
    return redirect(url_for('main.leaderboard'))

if __name__ == '__main__':
    app.run(debug=True)