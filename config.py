import os
from urllib.parse import quote_plus

class Config:
    SECRET_KEY = 'dev'  # Use your existing secret key here
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Supabase connection using transaction pooler
    db_password = quote_plus('Kahie805!?#')
    SQLALCHEMY_DATABASE_URI = f'postgresql://postgres.lywvaedilsbaautwqkmd:{db_password}@aws-0-us-east-2.pooler.supabase.com:6543/postgres'
    SQLALCHEMY_TRACK_MODIFICATIONS = False 