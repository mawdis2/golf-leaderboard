"""
Migration script to update trophy counts for existing tournament winners.
Run this script after deploying the code changes.
"""

import sys
import os
from collections import defaultdict

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import Tournament, TournamentResult, Player, Team, TeamMember, HistoricalTotal
from sqlalchemy import text

app = create_app()

def upgrade():
    with app.app_context():
        print("Adding trophy_count column to historical_total table if it doesn't exist...")
        try:
            db.session.execute(text("ALTER TABLE historical_total ADD COLUMN trophy_count INTEGER DEFAULT 0"))
            db.session.commit()
            print("Added trophy_count column successfully!")
        except Exception as e:
            print(f"Column may already exist or other error: {e}")
            db.session.rollback()
        
        print("Updating trophy counts for tournament winners...")
        
        # Get all tournament results with position 1 (winners)
        winner_results = TournamentResult.query.filter_by(position=1).all()
        
        # Track trophy counts by player and year
        trophy_counts = defaultdict(lambda: defaultdict(int))
        
        # First pass: count trophies for each player by year
        for result in winner_results:
            tournament = result.tournament
            year = tournament.date.year
            
            # For team winners
            if result.team_id:
                team = result.team
                print(f"Counting team winner: {team.name} for tournament {tournament.name}")
                
                for member in team.team_members:
                    player = member.player
                    trophy_counts[player.id][year] += 1
            
            # For individual winners
            elif result.player_id:
                player = result.player
                print(f"Counting individual winner: {player.name} for tournament {tournament.name}")
                trophy_counts[player.id][year] += 1
        
        # Second pass: update historical totals with trophy counts
        for player_id, year_counts in trophy_counts.items():
            player = Player.query.get(player_id)
            if not player:
                continue
                
            print(f"Updating trophy counts for {player.name}:")
            
            for year, count in year_counts.items():
                print(f"  Year {year}: {count} trophies")
                
                # Update or create historical total
                historical_total = HistoricalTotal.query.filter_by(
                    player_id=player_id,
                    year=year
                ).first()
                
                if historical_total:
                    historical_total.has_trophy = True
                    historical_total.trophy_count = count
                else:
                    historical_total = HistoricalTotal(
                        player_id=player_id,
                        year=year,
                        birdies=0,
                        eagles=0,
                        has_trophy=True,
                        trophy_count=count
                    )
                    db.session.add(historical_total)
        
        db.session.commit()
        print("Trophy counts updated successfully!")

if __name__ == "__main__":
    upgrade() 