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

# Initialize database (tables and admin user if they don't exist)
echo "==> Initializing database..."
python init_db.py

# Create migrations directory if it doesn't exist
mkdir -p migrations

# Create update_trophy_counts.py migration script
cat > migrations/update_trophy_counts.py << 'EOF'
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
EOF

# Run migration script to update trophy counts
echo "==> Running migration to update trophy counts..."
python migrations/update_trophy_counts.py

# Clean up
rm -f init_db.py 