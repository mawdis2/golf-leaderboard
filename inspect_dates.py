# inspect_dates.py
from models import db, Birdie

def inspect_dates():
    birdies = Birdie.query.all()
    for birdie in birdies:
        print(f"Birdie ID: {birdie.id}, Date: {birdie.date}, Type: {type(birdie.date)}")

if __name__ == "__main__":
    from create_app import create_app
    app = create_app()
    with app.app_context():
        inspect_dates()