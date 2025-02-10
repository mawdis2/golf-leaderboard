import os

class Config:
    SECRET_KEY = 'dev'  # Use your existing secret key here
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'birdie_tracker.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False 