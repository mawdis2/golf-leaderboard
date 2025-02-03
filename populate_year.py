# populate_year.py
from models import db, Birdie
from datetime import datetime

def populate_year():
    birdies = Birdie.query.all()
    for birdie in birdies:
        birdie.year = birdie.date.year
        db.session.commit()
        print(f"Updated birdie ID {birdie.id} to year {birdie.year}")

if __name__ == "__main__":
    from create_app import create_app
    app = create_app()
    with app.app_context():
        populate_year()