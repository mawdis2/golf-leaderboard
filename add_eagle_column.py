from create_app import create_app
from models import db

def add_eagle_column():
    app = create_app()
    with app.app_context():
        # Add the is_eagle column using raw SQL
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE birdie ADD COLUMN is_eagle BOOLEAN DEFAULT 0"))
            conn.commit()
        print("Added is_eagle column successfully!")

if __name__ == "__main__":
    add_eagle_column() 