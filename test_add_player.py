from app import app, db
from models import Player

def test_add_player():
    with app.app_context():
        try:
            # Create a new player
            new_player = Player(
                name="Test Player",
                has_trophy=False,
                permanent_emojis=None
            )
            
            # Add to session and commit
            db.session.add(new_player)
            db.session.commit()
            
            print(f"Successfully added player: {new_player.name} with ID: {new_player.id}")
            
            # Clean up - remove the test player
            db.session.delete(new_player)
            db.session.commit()
            print("Test player removed successfully")
            
        except Exception as e:
            print(f"Error adding player: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    test_add_player() 