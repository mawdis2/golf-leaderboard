# create_db.py
from models import db, User, Player, Birdie, Course
from create_app import create_app
import os

def create_database():
    app = create_app()
    
    # Get absolute path to instance directory
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    
    # Create instance directory if it doesn't exist
    os.makedirs(instance_path, exist_ok=True)
    
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

        # Create admin user if it doesn't exist
        admin = User(username='mawdisho')
        admin.set_password('admin')
        db.session.add(admin)

        # Restore the data
        for name, emojis in existing_players:
            player = Player(name=name, permanent_emojis=emojis, has_trophy=0)
            db.session.add(player)
        
        for name in existing_courses:
            course = Course(name=name)
            db.session.add(course)

        db.session.commit()

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