# app.py
from flask import Flask
from config import Config
from extensions import db, migrate, login_manager
from models import User  # Add this import

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
login_manager.login_view = 'main.login'

# Add this user_loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import and register the Blueprint
from routes import bp
app.register_blueprint(bp)

if __name__ == '__main__':
    app.run(debug=True)