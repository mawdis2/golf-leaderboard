from app import app, db

def check_sequence_state():
    with app.app_context():
        try:
            # Get current sequence value
            seq_value = db.session.execute("SELECT last_value FROM player_id_seq").scalar()
            print(f"Current sequence value: {seq_value}")
            
            # Get max ID from player table
            max_id = db.session.execute("SELECT MAX(id) FROM player").scalar()
            print(f"Max ID in player table: {max_id}")
            
            # Get all player IDs
            player_ids = db.session.execute("SELECT id FROM player ORDER BY id").fetchall()
            print("\nExisting player IDs:")
            for pid in player_ids:
                print(f"ID: {pid[0]}")
                
        except Exception as e:
            print(f"Error checking sequence: {str(e)}")

if __name__ == "__main__":
    check_sequence_state() 