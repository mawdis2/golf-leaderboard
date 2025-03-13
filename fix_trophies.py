import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, extract
from sqlalchemy.orm import sessionmaker

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import database models
from models import db, Player, Tournament, TournamentResult, HistoricalTotal, Team, TeamMember

def fix_trophy_records():
    print("Starting trophy record synchronization...")
    
    # Connect to the database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///birdie_leaderboard.db')
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all years with tournament data
        years_with_tournaments = session.query(
            extract('year', Tournament.date).label('year')
        ).distinct().all()
        tournament_years = [int(year.year) for year in years_with_tournaments]
        
        print(f"Years with tournaments: {tournament_years}")
        
        # Get all historical total records with trophies
        trophy_records = session.query(HistoricalTotal).filter(
            (HistoricalTotal.has_trophy == True) | (HistoricalTotal.trophy_count > 0)
        ).all()
        
        print(f"Found {len(trophy_records)} trophy records")
        
        # Process each trophy record
        for record in trophy_records:
            player = session.query(Player).filter_by(id=record.player_id).first()
            player_name = player.name if player else f"Player ID {record.player_id}"
            
            # Check if this year has tournaments
            if record.year not in tournament_years:
                print(f"Player {player_name} has trophy for year {record.year}, but no tournaments exist for this year")
                
                # Check if player has any tournament wins for this year
                team_wins = session.execute(text("""
                    SELECT COUNT(*) as win_count
                    FROM tournament_result tr
                    JOIN tournament t ON tr.tournament_id = t.id
                    JOIN team_member tm ON tr.team_id = tm.team_id
                    WHERE tm.player_id = :player_id
                    AND tr.position = 1
                    AND EXTRACT(YEAR FROM t.date) = :year
                """), {"player_id": record.player_id, "year": record.year}).fetchone()
                
                individual_wins = session.execute(text("""
                    SELECT COUNT(*) as win_count
                    FROM tournament_result tr
                    JOIN tournament t ON tr.tournament_id = t.id
                    WHERE tr.player_id = :player_id
                    AND tr.position = 1
                    AND EXTRACT(YEAR FROM t.date) = :year
                """), {"player_id": record.player_id, "year": record.year}).fetchone()
                
                team_win_count = team_wins.win_count if team_wins else 0
                individual_win_count = individual_wins.win_count if individual_wins else 0
                total_wins = team_win_count + individual_win_count
                
                print(f"  - Team wins: {team_win_count}")
                print(f"  - Individual wins: {individual_win_count}")
                print(f"  - Total wins: {total_wins}")
                
                if total_wins == 0:
                    print(f"  - Removing trophy for {player_name} in {record.year}")
                    record.has_trophy = False
                    record.trophy_count = 0
                else:
                    print(f"  - Keeping trophy for {player_name} in {record.year} ({total_wins} wins)")
                    record.trophy_count = total_wins
        
        # Commit changes
        session.commit()
        print("Trophy records synchronized successfully")
        
    except Exception as e:
        print(f"Error synchronizing trophy records: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_trophy_records() 