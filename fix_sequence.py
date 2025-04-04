from app import app, db

def fix_sequence():
    with app.app_context():
        try:
            # Get max ID from player table
            max_id = db.session.execute("SELECT MAX(id) FROM player").scalar()
            if max_id is None:
                max_id = 0
                
            # Set sequence to next available ID
            next_id = max_id + 1
            db.session.execute(f"ALTER SEQUENCE player_id_seq RESTART WITH {next_id}")
            db.session.commit()
            
            print(f"Sequence reset to start from {next_id}")
            
            # Verify the new sequence value
            new_value = db.session.execute("SELECT last_value FROM player_id_seq").scalar()
            print(f"New sequence value: {new_value}")
            
        except Exception as e:
            print(f"Error fixing sequence: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    fix_sequence() 