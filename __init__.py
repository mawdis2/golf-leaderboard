from flask import Flask
from .config import Config
from .extensions import db, migrate, login_manager
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Create instance directory if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    from .routes import bp
    app.register_blueprint(bp)
    
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

# ... rest of your initialization code ... 