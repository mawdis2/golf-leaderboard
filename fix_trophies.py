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
        
        # Get all players
        players = session.query(Player).all()
        
        # Process each player for each year
        for year in tournament_years:
            print(f"\nChecking year {year}:")
            
            for player in players:
                print(f"Checking trophy records for {player.name}...")
                
                # Count individual tournament wins
                individual_wins = session.execute(text("""
                    SELECT COUNT(*) as win_count
                    FROM tournament_result tr
                    JOIN tournament t ON tr.tournament_id = t.id
                    WHERE tr.player_id = :player_id
                    AND tr.position = 1
                    AND EXTRACT(YEAR FROM t.date) = :year
                """), {"player_id": player.id, "year": year}).fetchone()
                
                # Count team tournament wins
                team_wins_query = text("""
                    SELECT COUNT(*) as win_count
                    FROM tournament_result tr
                    JOIN tournament t ON tr.tournament_id = t.id
                    JOIN team_member tm ON tr.team_id = tm.team_id
                    WHERE tm.player_id = :player_id
                    AND tr.position = 1
                    AND EXTRACT(YEAR FROM t.date) = :year
                """)
                team_wins = session.execute(team_wins_query, {"player_id": player.id, "year": year}).fetchone()
                
                individual_win_count = individual_wins.win_count if individual_wins else 0
                team_win_count = team_wins.win_count if team_wins else 0
                total_wins = individual_win_count + team_win_count
                
                print(f"  - Individual wins: {individual_win_count}")
                print(f"  - Team wins: {team_win_count}")
                print(f"  - Total wins: {total_wins}")
                
                # Get or create historical total record
                historical_total = session.query(HistoricalTotal).filter_by(
                    player_id=player.id,
                    year=year
                ).first()
                
                if total_wins > 0:
                    # Player should have a trophy
                    if not historical_total:
                        # Create new historical total
                        print(f"  - Creating new historical total for {player.name} in {year} with trophy")
                        historical_total = HistoricalTotal(
                            player_id=player.id,
                            year=year,
                            birdies=0,
                            eagles=0,
                            has_trophy=True,
                            trophy_count=total_wins
                        )
                        session.add(historical_total)
                    else:
                        # Update existing historical total
                        print(f"  - Updating historical total for {player.name} in {year} with trophy")
                        historical_total.has_trophy = True
                        historical_total.trophy_count = total_wins
                        
                    # Update player's permanent emojis
                    if not player.permanent_emojis:
                        player.permanent_emojis = "🏆"
                    elif "🏆" not in player.permanent_emojis:
                        player.permanent_emojis += "🏆"
                        
                elif historical_total and historical_total.has_trophy:
                    # Player has a trophy record but no tournament wins
                    print(f"  - Removing trophy for {player.name} in {year} (no tournament wins found)")
                    historical_total.has_trophy = False
                    historical_total.trophy_count = 0
        
        # Special check for Carlo in 2024
        carlo = session.query(Player).filter(Player.name.like('%Carlo%')).first()
        if carlo:
            print(f"\nSpecial check for {carlo.name} in 2024:")
            
            # Check for tournament wins in 2024
            individual_wins = session.execute(text("""
                SELECT t.name, t.date
                FROM tournament_result tr
                JOIN tournament t ON tr.tournament_id = t.id
                WHERE tr.player_id = :player_id
                AND tr.position = 1
                AND EXTRACT(YEAR FROM t.date) = 2024
            """), {"player_id": carlo.id}).fetchall()
            
            team_wins = session.execute(text("""
                SELECT t.name, t.date, team.name as team_name
                FROM tournament_result tr
                JOIN tournament t ON tr.tournament_id = t.id
                JOIN team ON tr.team_id = team.id
                JOIN team_member tm ON tr.team_id = tm.team_id
                WHERE tm.player_id = :player_id
                AND tr.position = 1
                AND EXTRACT(YEAR FROM t.date) = 2024
            """), {"player_id": carlo.id}).fetchall()
            
            print(f"  - Individual wins: {len(individual_wins)}")
            for win in individual_wins:
                print(f"    - {win.name} on {win.date}")
                
            print(f"  - Team wins: {len(team_wins)}")
            for win in team_wins:
                print(f"    - {win.name} on {win.date} with team {win.team_name}")
            
            total_wins = len(individual_wins) + len(team_wins)
            
            # Ensure Carlo has a trophy for 2024 if he won any tournaments
            if total_wins > 0:
                historical_total = session.query(HistoricalTotal).filter_by(
                    player_id=carlo.id,
                    year=2024
                ).first()
                
                if not historical_total:
                    print(f"  - Creating new historical total for {carlo.name} in 2024 with trophy")
                    historical_total = HistoricalTotal(
                        player_id=carlo.id,
                        year=2024,
                        birdies=0,
                        eagles=0,
                        has_trophy=True,
                        trophy_count=total_wins
                    )
                    session.add(historical_total)
                else:
                    print(f"  - Updating historical total for {carlo.name} in 2024 with trophy")
                    historical_total.has_trophy = True
                    historical_total.trophy_count = total_wins
                
                # Update Carlo's permanent emojis
                if not carlo.permanent_emojis:
                    carlo.permanent_emojis = "🏆"
                elif "🏆" not in carlo.permanent_emojis:
                    carlo.permanent_emojis += "🏆"
        
        # Commit changes
        session.commit()
        print("\nTrophy records synchronized successfully")
        
    except Exception as e:
        print(f"Error synchronizing trophy records: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_trophy_records() 