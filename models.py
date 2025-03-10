# models.py
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager
from datetime import datetime
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    has_trophy = db.Column(db.Boolean, default=False)
    permanent_emojis = db.Column(db.String(50))
    birdies = db.relationship('Birdie', backref='player', lazy=True)
    eagles = db.relationship('Eagle', backref='player', lazy=True)
    historical_totals = db.relationship('HistoricalTotal', backref='player', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "permanent_emojis": self.permanent_emojis
        }

class Birdie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    hole_number = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    is_eagle = db.Column(db.Boolean, default=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class HistoricalTotal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    birdies = db.Column(db.Integer, default=0)
    eagles = db.Column(db.Integer, default=0)
    has_trophy = db.Column(db.Boolean, default=False)
    
    __table_args__ = (db.UniqueConstraint('player_id', 'year', name='unique_player_year'),)

class Eagle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    hole_number = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Eagle {self.player_id} {self.course_id} {self.hole_number}>'