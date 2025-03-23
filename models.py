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
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    has_trophy = db.Column(db.Boolean, default=False)
    permanent_emojis = db.Column(db.String(64), nullable=True)
    
    birdies = db.relationship('Birdie', backref='player', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }

class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    
    birdies = db.relationship('Birdie', backref='course', lazy='dynamic')

class Birdie(db.Model):
    __tablename__ = 'birdie'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    hole_number = db.Column(db.Integer)
    year = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_eagle = db.Column(db.Boolean, default=False)

class HistoricalTotal(db.Model):
    __tablename__ = 'historical_total'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    year = db.Column(db.Integer)
    birdies = db.Column(db.Integer, default=0)
    eagles = db.Column(db.Integer, default=0)
    has_trophy = db.Column(db.Boolean, default=False)
    trophy_count = db.Column(db.Integer, default=0)

class Eagle(db.Model):
    __tablename__ = 'eagle'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    hole_number = db.Column(db.Integer)
    year = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# New models for tournaments

class Tournament(db.Model):
    __tablename__ = 'tournament'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    has_individual_matches = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    results = db.relationship('TournamentResult', backref='tournament', lazy=True)
    course = db.relationship('Course', backref='tournaments')
    
    def __repr__(self):
        return f'<Tournament: {self.name}>'
    
    def get_standings(self):
        if self.has_individual_matches:
            # Calculate standings based on match results
            standings = {}
            for match in self.matches:
                if match.is_tie:
                    standings[match.player1_id] = standings.get(match.player1_id, 0) + 0.5
                    standings[match.player2_id] = standings.get(match.player2_id, 0) + 0.5
                elif match.winner_id:
                    standings[match.winner_id] = standings.get(match.winner_id, 0) + 1
            
            # Convert to list of tuples (player_id, points) and sort
            sorted_standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)
            return [(Player.query.get(player_id), points) for player_id, points in sorted_standings]
        else:
            # Use regular tournament results
            return sorted(self.results, key=lambda x: x.position)

class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    
    # Relationships
    team_members = db.relationship('TeamMember', backref='team', cascade='all, delete-orphan')
    results = db.relationship('TournamentResult', backref='team')
    
    def __repr__(self):
        return f'<Team {self.name}>'

class TeamMember(db.Model):
    __tablename__ = 'team_member'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    # Relationship
    player = db.relationship('Player', backref='team_memberships')
    
    def __repr__(self):
        return f'<TeamMember {self.player.name} in {self.team.name}>'

class TournamentResult(db.Model):
    __tablename__ = 'tournament_result'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    position = db.Column(db.Integer, nullable=False)  # 1 for winner, 2 for runner-up, etc.
    score = db.Column(db.String(32), nullable=True)  # Could be strokes, points, etc.
    
    # Relationships
    player = db.relationship('Player', backref='tournament_results')
    
    def __repr__(self):
        if self.team_id:
            return f'<Result: Tournament {self.tournament.name} - Team {self.team.name} - Position {self.position}>'
        else:
            return f'<Result: Tournament {self.tournament.name} - Player {self.player.name} - Position {self.position}>'

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    is_tie = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tournament = db.relationship('Tournament', backref=db.backref('matches', lazy=True))
    player1 = db.relationship('Player', foreign_keys=[player1_id], backref='matches_as_player1')
    player2 = db.relationship('Player', foreign_keys=[player2_id], backref='matches_as_player2')
    winner = db.relationship('Player', foreign_keys=[winner_id], backref='matches_won')