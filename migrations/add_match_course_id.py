from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_match_course_id():
    with app.app_context():
        print("Adding course_id column to match table...")
        try:
            # Add the column
            db.session.execute(text("ALTER TABLE match ADD COLUMN course_id INTEGER REFERENCES course(id)"))
            
            # Set default course_id for existing matches
            default_course = db.session.execute(text("SELECT id FROM course LIMIT 1")).fetchone()
            if default_course:
                db.session.execute(text(f"UPDATE match SET course_id = {default_course[0]} WHERE course_id IS NULL"))
            
            # Make the column not null
            db.session.execute(text("ALTER TABLE match ALTER COLUMN course_id SET NOT NULL"))
            
            db.session.commit()
            print("Successfully added course_id column to match table")
        except Exception as e:
            print(f"Error adding course_id column: {e}")
            db.session.rollback()

if __name__ == '__main__':
    add_match_course_id() 