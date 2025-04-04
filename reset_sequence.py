from app import app, db
from sqlalchemy import inspect

def reset_player_sequence():
    with app.app_context():
        try:
            # Get the maximum ID from the player table
            result = db.session.execute("SELECT MAX(id) FROM player").scalar()
            max_id = result if result is not None else 0
            
            # Check if we're using PostgreSQL (Supabase) or SQLite
            inspector = inspect(db.engine)
            if inspector.dialect.name == 'postgresql':
                # For PostgreSQL/Supabase
                db.session.execute(f"SELECT setval('player_id_seq', {max_id}, true)")
                current_val = db.session.execute("SELECT currval('player_id_seq')").scalar()
                print(f"PostgreSQL: Reset sequence to {current_val}")
            else:
                print("Running in SQLite mode - sequence reset not needed")
            
            db.session.commit()
            print(f"Successfully reset player sequence to start from {max_id + 1}")
            
        except Exception as e:
            print(f"Error resetting sequence: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    reset_player_sequence() 