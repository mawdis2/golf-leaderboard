# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    permanent_emojis = db.Column(db.String(255), default="")  # New column for permanent emojis

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
    date = db.Column(db.Date, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    is_eagle = db.Column(db.Boolean, default=False)  # New column

    player = db.relationship('Player', backref=db.backref('birdies', lazy=True))
    course = db.relationship('Course', backref=db.backref('birdies', lazy=True))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class HistoricalTotal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_birdies = db.Column(db.Integer, default=0)
    total_eagles = db.Column(db.Integer, default=0)
    has_trophy = db.Column(db.Boolean, default=False)
    
    player = db.relationship('Player', backref=db.backref('historical_totals', lazy=True))
    
    __table_args__ = (db.UniqueConstraint('player_id', 'year', name='unique_player_year'),)

class Eagle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    course = db.Column(db.String(100), nullable=False)
    hole = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    year = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Eagle {self.player_id} {self.course} {self.hole}>'