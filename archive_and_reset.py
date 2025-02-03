# archive_and_reset.py
from models import db, Birdie
from datetime import datetime

def archive_and_reset():
    current_year = datetime.now().year
    previous_year = current_year - 1

    # Archive previous year's data
    birdies_previous_year = Birdie.query.filter_by(year=previous_year).all()
    for birdie in birdies_previous_year:
        # Archive logic here (e.g., move to a different table or save to a file)
        pass

    # Delete previous year's data
    Birdie.query.filter_by(year=previous_year).delete()
    db.session.commit()
    print(f"Archived and deleted birdies for the year {previous_year}.")

if __name__ == "__main__":
    from create_app import create_app
    app = create_app()
    with app.app_context():
        archive_and_reset()