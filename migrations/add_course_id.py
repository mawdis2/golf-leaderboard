from app import create_app, db
from models import Tournament

def add_course_id():
    app = create_app()
    with app.app_context():
        try:
            # Add course_id column
            db.session.execute('ALTER TABLE tournament ADD COLUMN course_id INTEGER REFERENCES course(id)')
            db.session.commit()
            print("Successfully added course_id column to tournament table")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding course_id column: {e}")

if __name__ == '__main__':
    add_course_id() 