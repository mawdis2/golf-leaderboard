"""
Migration script to award trophies to existing tournament winners.
Run this script after deploying the code changes.
"""

import sys
import os

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import Tournament, TournamentResult, Player, Team, TeamMember, HistoricalTotal

app = create_app()

def upgrade():
    with app.app_context():
        print("Awarding trophies to tournament winners...")
        
        # Get all tournament results with position 1 (winners)
        winner_results = TournamentResult.query.filter_by(position=1).all()
        
        trophy_count = 0
        
        for result in winner_results:
            tournament = result.tournament
            year = tournament.date.year
            
            # For team winners
            if result.team_id:
                team = result.team
                print(f"Processing team winner: {team.name} for tournament {tournament.name}")
                
                for member in team.team_members:
                    player = member.player
                    print(f"  Awarding trophy to team member: {player.name}")
                    
                    # Add trophy to player's permanent emojis
                    if not player.permanent_emojis:
                        player.permanent_emojis = "🏆"
                    elif "🏆" not in player.permanent_emojis:
                        player.permanent_emojis += "🏆"
                    
                    # Update or create historical total
                    historical_total = HistoricalTotal.query.filter_by(
                        player_id=player.id,
                        year=year
                    ).first()
                    
                    if not historical_total:
                        historical_total = HistoricalTotal(
                            player_id=player.id,
                            year=year,
                            birdies=0,
                            eagles=0,
                            has_trophy=True
                        )
                        db.session.add(historical_total)
                    else:
                        historical_total.has_trophy = True
                    
                    trophy_count += 1
            
            # For individual winners
            elif result.player_id:
                player = result.player
                print(f"Processing individual winner: {player.name} for tournament {tournament.name}")
                
                # Add trophy to player's permanent emojis
                if not player.permanent_emojis:
                    player.permanent_emojis = "🏆"
                elif "🏆" not in player.permanent_emojis:
                    player.permanent_emojis += "🏆"
                
                # Update or create historical total
                historical_total = HistoricalTotal.query.filter_by(
                    player_id=player.id,
                    year=year
                ).first()
                
                if not historical_total:
                    historical_total = HistoricalTotal(
                        player_id=player.id,
                        year=year,
                        birdies=0,
                        eagles=0,
                        has_trophy=True
                    )
                    db.session.add(historical_total)
                else:
                    historical_total.has_trophy = True
                
                trophy_count += 1
        
        db.session.commit()
        print(f"Awarded {trophy_count} trophies to tournament winners!")

if __name__ == "__main__":
    upgrade() 