from models import db
from app import app
from sqlalchemy import text

with app.app_context():
    # Add the column
    with db.engine.connect() as conn:
        conn.execute(text('ALTER TABLE historical_total ADD COLUMN has_trophy BOOLEAN DEFAULT FALSE'))
        conn.commit()

    print("Trophy column added successfully!") 