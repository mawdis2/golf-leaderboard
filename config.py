import os

class Config:
    SECRET_KEY = 'dev'  # Use your existing secret key here
    SQLALCHEMY_DATABASE_URI = 'sqlite:///birdie_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False 