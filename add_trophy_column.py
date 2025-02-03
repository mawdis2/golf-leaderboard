from create_app import create_app
from models import db

def add_trophy_column():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE player ADD COLUMN has_trophy BOOLEAN DEFAULT 0"))
            conn.commit()
        print("Added has_trophy column successfully!")

if __name__ == "__main__":
    add_trophy_column() 