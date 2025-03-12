"""
Migration script to fix trophy counts by directly counting tournament wins.
Run this script after deploying the code changes.
"""

import sys
import os
from collections import defaultdict
from sqlalchemy import extract

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import Tournament, TournamentResult, Player, Team, TeamMember, HistoricalTotal
from sqlalchemy import text

app = create_app()

def fix_trophy_counts():
    with app.app_context():
        print("Fixing trophy counts by directly counting tournament wins...")
        
        # Get all players
        players = Player.query.all()
        
        # Get all years with tournaments
        years_query = db.session.query(
            db.distinct(extract('year', Tournament.date))
        ).all()
        years = [year[0] for year in years_query]
        
        # Track updates
        updates_made = 0
        
        # Process each player
        for player in players:
            print(f"\nChecking trophy counts for {player.name}...")
            
            # Process each year
            for year in years:
                # Count individual tournament wins
                individual_wins = TournamentResult.query.join(Tournament).filter(
                    TournamentResult.player_id == player.id,
                    TournamentResult.position == 1,
                    extract('year', Tournament.date) == year
                ).count()
                
                # Count team tournament wins
                team_wins = 0
                teams = Team.query.join(TeamMember).filter(TeamMember.player_id == player.id).all()
                for team in teams:
                    team_wins += TournamentResult.query.join(Tournament).filter(
                        TournamentResult.team_id == team.id,
                        TournamentResult.position == 1,
                        extract('year', Tournament.date) == year
                    ).count()
                
                # Total trophy count for this year
                actual_trophy_count = individual_wins + team_wins
                
                if actual_trophy_count > 0:
                    print(f"  Year {year}: {actual_trophy_count} trophies ({individual_wins} individual, {team_wins} team)")
                    
                    # Get or create historical total
                    historical_total = HistoricalTotal.query.filter_by(
                        player_id=player.id,
                        year=year
                    ).first()
                    
                    if historical_total:
                        current_count = getattr(historical_total, 'trophy_count', 0) or 0
                        if current_count != actual_trophy_count:
                            print(f"  Updating trophy count from {current_count} to {actual_trophy_count}")
                            historical_total.has_trophy = True
                            historical_total.trophy_count = actual_trophy_count
                            updates_made += 1
                    else:
                        print(f"  Creating new historical total with {actual_trophy_count} trophies")
                        historical_total = HistoricalTotal(
                            player_id=player.id,
                            year=year,
                            birdies=0,
                            eagles=0,
                            has_trophy=True,
                            trophy_count=actual_trophy_count
                        )
                        db.session.add(historical_total)
                        updates_made += 1
                    
                    # Ensure player has trophy emoji
                    if not player.permanent_emojis:
                        player.permanent_emojis = "🏆"
                        print(f"  Added trophy emoji to player")
                    elif "🏆" not in player.permanent_emojis:
                        player.permanent_emojis += "🏆"
                        print(f"  Added trophy emoji to player")
        
        # Commit changes
        if updates_made > 0:
            print(f"\nCommitting {updates_made} updates to the database...")
            db.session.commit()
            print("Trophy counts fixed successfully!")
        else:
            print("\nNo updates needed. Trophy counts are already correct.")

if __name__ == "__main__":
    fix_trophy_counts() 