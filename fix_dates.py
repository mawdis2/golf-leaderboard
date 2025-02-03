# fix_dates.py
from models import db, Birdie
from datetime import datetime

def fix_dates():
    birdies = Birdie.query.all()
    for birdie in birdies:
        print(f"Original Birdie Date: {birdie.date}, Type: {type(birdie.date)}")
        if isinstance(birdie.date, int) and len(str(birdie.date)) == 4:  # If the date is only the year
            birdie.date = datetime.strptime(f"{birdie.date}-01-01", '%Y-%m-%d').date()
            db.session.commit()
            print(f"Updated birdie ID {birdie.id} to date {birdie.date}")
        elif isinstance(birdie.date, str):
            try:
                birdie.date = datetime.strptime(birdie.date, '%Y-%m-%d').date()
                db.session.commit()
                print(f"Updated birdie ID {birdie.id} to date {birdie.date}")
            except ValueError:
                print(f"Skipping birdie ID {birdie.id} with invalid date format: {birdie.date}")
        else:
            print(f"Skipping birdie ID {birdie.id} with unrecognized date type: {birdie.date}")

if __name__ == "__main__":
    from create_app import create_app
    app = create_app()
    with app.app_context():
        fix_dates()