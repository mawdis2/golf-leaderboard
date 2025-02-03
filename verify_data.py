# verify_data.py
from models import db, Birdie, Player
from create_app import create_app

def verify_data():
    app = create_app()
    with app.app_context():
        players = Player.query.all()
        birdies = Birdie.query.all()
        print(f"Players in the database: {len(players)}")
        for player in players:
            print(f"Player ID: {player.id}, Name: {player.name}")

        print(f"Birdies in the database: {len(birdies)}")
        for birdie in birdies:
            print(f"Birdie ID: {birdie.id}, Player ID: {birdie.player_id}, Date: {birdie.date}, Year: {birdie.year}")

if __name__ == "__main__":
    verify_data()