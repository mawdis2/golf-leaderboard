# create_app.py
from flask import Flask
from models import db
from flask_login import LoginManager
from datetime import timedelta
import os

def create_app():
    app = Flask(__name__)
    
    # Get absolute path to the database file
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'golf_leaderboard.db')
    
    # Create instance directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'mawdisho-golf-app-2025'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes import bp
    app.register_blueprint(bp)
    
    return app