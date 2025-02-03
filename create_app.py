# create_app.py
from flask import Flask, render_template
from models import db, User  # Import db and User from models.py
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///golf_leaderboard.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'  # Add a secret key for flash messages

    print("App created")

    # Initialize SQLAlchemy with Flask
    db.init_app(app)

    # Initialize Flask-Migrate with Flask and SQLAlchemy
    migrate = Migrate(app, db)

    with app.app_context():
        db.create_all()

        # Create an admin user if not exists
        if not User.query.filter_by(username='mawdisho').first():
            admin = User(username='mawdisho', is_admin=True)
            admin.set_password('ign')
            db.session.add(admin)
            db.session.commit()

        # Import routes here to avoid circular imports
        import routes

        # Define home route
        @app.route("/")
        def home():
            print("Home route accessed")
            return render_template("index.html", title="Welcome to My Website")

    return app