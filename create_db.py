# create_db.py
from models import db, User, Player, Birdie, Course, Eagle
from create_app import create_app

def create_database():
    app = create_app()
    with app.app_context():
        # Backup existing data
        try:
            existing_players = [(p.name, p.permanent_emojis) for p in Player.query.all()]
            existing_courses = [c.name for c in Course.query.all()]
            existing_birdies = [(b.player_id, b.course, b.date, b.year, b.is_eagle) for b in Birdie.query.all()]
        except:
            existing_players = []
            existing_courses = []
            existing_birdies = []

        # Drop and recreate all tables
        db.drop_all()
        db.create_all()

        # Restore the data
        for name, emojis in existing_players:
            player = Player(name=name, permanent_emojis=emojis, has_trophy=False)
            db.session.add(player)
        
        for name in existing_courses:
            course = Course(name=name)
            db.session.add(course)

        db.session.commit()  # Commit to get IDs for players and courses

        # Restore birdies
        for player_id, course, date, year, is_eagle in existing_birdies:
            birdie = Birdie(
                player_id=player_id,
                course=course,
                date=date,
                year=year,
                is_eagle=is_eagle
            )
            db.session.add(birdie)

        db.session.commit()
        print("Database recreated successfully with all data preserved!")

if __name__ == "__main__":
    create_database()