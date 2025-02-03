from create_app import create_app
from models import db, Birdie, Player

def backup_data():
    app = create_app()
    with app.app_context():
        # Backup existing birdies
        birdies = Birdie.query.all()
        birdie_data = [(b.player_id, b.course_id, b.date, b.year) for b in birdies]
        
        # Drop and recreate the table
        Birdie.__table__.drop(db.engine)
        db.create_all()
        
        # Restore the data with is_eagle=False for existing records
        for player_id, course_id, date, year in birdie_data:
            new_birdie = Birdie(
                player_id=player_id,
                course_id=course_id,
                date=date,
                year=year,
                is_eagle=False
            )
            db.session.add(new_birdie)
        
        db.session.commit()
        print("Database updated successfully!")

if __name__ == "__main__":
    backup_data() 