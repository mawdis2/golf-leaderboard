from app import app, db

def reset_player_sequence():
    with app.app_context():
        try:
            # Get the maximum ID from the player table
            result = db.session.execute("SELECT MAX(id) FROM player").scalar()
            max_id = result if result is not None else 0
            
            # For Supabase, we need to use the specific sequence name
            # The sequence name in Supabase is typically 'player_id_seq'
            db.session.execute(f"SELECT setval('player_id_seq', {max_id}, true)")
            
            # Verify the sequence value
            current_val = db.session.execute("SELECT currval('player_id_seq')").scalar()
            print(f"Current sequence value: {current_val}")
            
            db.session.commit()
            print(f"Successfully reset player sequence to start from {max_id + 1}")
            
        except Exception as e:
            print(f"Error resetting sequence: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    reset_player_sequence() 