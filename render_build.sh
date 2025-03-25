#!/usr/bin/env bash
# Exit on error
set -o errexit

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Install dependencies
echo "==> Installing dependencies..."
pip install -r requirements.txt

# Create database initialization script
cat > init_db.py << 'EOF'
import os, sys, time
from sqlalchemy import text, inspect, MetaData
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import create_app
from extensions import db
from models import User, Player, Course, Birdie, HistoricalTotal
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    try:
        print(f"  -> Database URL: {db.engine.url}")
        print("  -> Testing database connection...")
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("  -> Database connection successful")

        # Check if tables exist first
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'users' not in tables:
            # If tables don't exist, create schema and tables
            print("  -> Setting up schema...")
            with db.engine.connect() as conn:
                conn.execute(text('COMMIT'))
                conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
                conn.execute(text('CREATE SCHEMA public'))
                conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
                conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
                conn.execute(text('COMMIT'))

            # Create tables
            print("  -> Creating tables...")
            db.create_all()
            
            # Create admin user
            print("  -> Creating admin user...")
            password_hash = generate_password_hash('ign')
            admin = User(username='mawdisho', password_hash=password_hash, is_admin=True)
            db.session.add(admin)
            db.session.commit()
        else:
            print("  -> Tables already exist, skipping schema creation")
            
            # Check if trophy_count column exists in historical_total table
            # If not, add it
            print("  -> Checking for trophy_count column...")
            try:
                db.session.execute(text("SELECT trophy_count FROM historical_total LIMIT 1"))
                print("  -> trophy_count column already exists")
            except Exception:
                print("  -> Adding trophy_count column to historical_total table...")
                try:
                    db.session.execute(text("ALTER TABLE historical_total ADD COLUMN trophy_count INTEGER DEFAULT 0"))
                    db.session.commit()
                    print("  -> trophy_count column added successfully")
                except Exception as e:
                    db.session.rollback()
                    print(f"  -> Error adding trophy_count column: {e}")

        # Set permissions
        print("  -> Setting permissions...")
        with db.engine.begin() as conn:
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO public'))
            conn.execute(text('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO public'))

        # Verify tables
        print("  -> Verifying tables...")
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"    - Found tables: {tables}")
        
        for table in ['users', 'player', 'course', 'birdie', 'historical_total']:
            if table not in tables:
                raise Exception(f"Table {table} was not created successfully")
            columns = [c['name'] for c in inspector.get_columns(table)]
            print(f"    - Verified table {table}:")
            print(f"      Columns: {columns}")

        # Verify admin user
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM users WHERE username = 'mawdisho'")).first()
            if result:
                print("  -> Admin user verified successfully")
            else:
                raise Exception("Admin user was not created successfully")

        print(f"==> Database initialized successfully in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        import traceback
        print("  -> Full error details:")
        traceback.print_exc()
        sys.exit(1)
EOF

# Initialize database
echo "==> Initializing database..."
python init_db.py

# Run migrations
echo "==> Running migrations..."
python migrations/add_has_individual_matches.py
python migrations/add_is_active.py
python migrations/add_created_at.py
python migrations/add_course_id.py
python migrations/add_year_column.py
python migrations/add_match_course_id.py

# Create migrations directory if it doesn't exist
mkdir -p migrations/versions

# Create fix_trophy_counts.py migration script
cat > migrations/fix_trophy_counts.py << 'EOF'
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
EOF

# Run fix_trophy_counts.py script
echo "==> Running fix_trophy_counts.py script..."
python migrations/fix_trophy_counts.py

# Clean up
rm -f init_db.py 

# Start the application
echo "==> Starting application..."
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --daemon 