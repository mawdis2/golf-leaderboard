# app.py
from create_app import create_app
import routes  # Add this line to import routes
from flask_migrate import Migrate
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config  # Import your existing config

app = Flask(__name__)
app.config.from_object(Config)  # Use your existing config

db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'

if __name__ == "__main__":
    print("Starting Flask app")
    app.run(debug=True)