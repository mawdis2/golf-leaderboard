# app.py
from . import app
from .config import Config
from .extensions import db, migrate, login_manager
from .models import User

migrate.init_app(app, db)
login_manager.init_app(app)

# Remove the blueprint registration line
# app.register_blueprint(bp)  # This line should be removed

if __name__ == '__main__':
    app.run(debug=True)