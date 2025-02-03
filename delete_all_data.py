# delete_all_data.py
from models import db, User, Player, Birdie, Course
from create_app import create_app

def delete_all_data():
    app = create_app()
    with app.app_context():
        db.session.query(User).delete()
        db.session.query(Player).delete()
        db.session.query(Birdie).delete()
        db.session.query(Course).delete()
        db.session.commit()
        print("All data deleted from all tables.")

if __name__ == "__main__":
    delete_all_data()