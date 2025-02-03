from create_app import create_app
from models import db, Player, Birdie
from datetime import datetime

def fix_eagle_emojis():
    app = create_app()
    with app.app_context():
        current_year = datetime.now().year
        players = Player.query.all()
        
        for player in players:
            # Count total eagles for this player this year
            eagle_count = Birdie.query.filter_by(
                player_id=player.id,
                year=current_year,
                is_eagle=True
            ).count()
            
            # Update player's permanent emojis
            player.permanent_emojis = "🦅" * eagle_count
        
        db.session.commit()
        print("Eagle emojis updated for all players!")

if __name__ == "__main__":
    fix_eagle_emojis() 