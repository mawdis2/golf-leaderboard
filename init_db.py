import os, sys, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import create_app
from extensions import db
from models import User, Player, Course, Birdie, HistoricalTotal, Eagle, Tournament, Team, TeamMember, TournamentResult, Match
from sqlalchemy import inspect, text, create_engine
from flask import Flask
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy.exc import OperationalError, ProgrammingError

def verify_table_exists(table_name, inspector):
    tables = inspector.get_table_names()
    exists = table_name in tables
    print(f"  -> Checking table '{table_name}': {'EXISTS' if exists else 'MISSING'}")
    return exists

def verify_table_columns(table_name, inspector):
    columns = inspector.get_columns(table_name)
    print(f"  -> Table '{table_name}' columns:")
    for column in columns:
        print(f"     - {column['name']}: {column['type']}")

app = create_app()

def init_db():
    try:
        print("==> Starting database setup...")
        
        # Get database URL from environment variable
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("Error: DATABASE_URL environment variable not set")
            sys.exit(1)
        
        print(f"  -> Database URL: {database_url}")
        
        # Create engine and test connection
        print("  -> Testing database connection...")
        engine = create_engine(database_url)
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("  -> Database connection successful")
        except Exception as e:
            print(f"  -> Error connecting to database: {e}")
            sys.exit(1)
        
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            print("  -> Tables already exist, skipping schema creation")
            
            # Check for trophy_count column
            print("  -> Checking for trophy_count column...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT trophy_count FROM historical_total LIMIT 1"))
                print("  -> trophy_count column already exists")
            except Exception:
                print("  -> Adding trophy_count column...")
                try:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE historical_total ADD COLUMN trophy_count INTEGER DEFAULT 0"))
                    print("  -> trophy_count column added successfully")
                except Exception as e:
                    print(f"  -> Error adding trophy_count column: {e}")
            
            # Check for has_individual_matches column
            print("  -> Checking for has_individual_matches column...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT has_individual_matches FROM tournament LIMIT 1"))
                print("  -> has_individual_matches column already exists")
            except Exception:
                print("  -> Adding has_individual_matches column...")
                try:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE tournament ADD COLUMN has_individual_matches BOOLEAN DEFAULT FALSE"))
                    print("  -> has_individual_matches column added successfully")
                except Exception as e:
                    print(f"  -> Error adding has_individual_matches column: {e}")
            
            # Set permissions
            print("  -> Setting permissions...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO golf_leaderboard_db_user"))
                    conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO golf_leaderboard_db_user"))
                print("  -> Permissions set successfully")
            except Exception as e:
                print(f"  -> Error setting permissions: {e}")
            
            # Verify tables
            print("  -> Verifying tables...")
            try:
                with engine.connect() as conn:
                    # Get all tables
                    result = conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """))
                    tables = [row[0] for row in result]
                    print(f"    - Found tables: {tables}")
                    
                    # Verify each table's columns
                    for table in tables:
                        result = conn.execute(text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = '{table}'
                        """))
                        columns = [row[0] for row in result]
                        print(f"    - Verified table {table}:")
                        print(f"      Columns: {columns}")
                    
                    # Verify admin user
                    result = conn.execute(text("SELECT * FROM users WHERE username = 'admin'"))
                    admin = result.fetchone()
                    if admin:
                        print("  -> Admin user verified successfully")
                    else:
                        print("  -> Admin user not found, creating...")
                        conn.execute(text("""
                            INSERT INTO users (username, password_hash, is_admin)
                            VALUES ('admin', 'pbkdf2:sha256:260000$YOUR_HASH_HERE', true)
                        """))
                        print("  -> Admin user created successfully")
            except Exception as e:
                print(f"  -> Error verifying tables: {e}")
        else:
            print("  -> Creating database schema...")
            db.create_all()
            print("  -> Database schema created successfully")
            
            # Create admin user
            print("  -> Creating admin user...")
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin')  # Change this in production
            db.session.add(admin)
            db.session.commit()
            print("  -> Admin user created successfully")
        
        print(f"\n==> Database initialization completed in {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"==> Database initialization error: {e}")
        sys.exit(1)

def verify_db():
    print("==> Verifying final database state...")
    app = create_app()
    
    with app.app_context():
        tables = db.engine.table_names()
        print(f"Tables in the database: {tables}")
        
        # Check if Birdie table exists
        if 'birdie' in tables:
            result = db.session.execute(text("SELECT COUNT(*) FROM birdie"))
            count = result.scalar()
            print(f"The Birdie table has {count} records.")
        else:
            print("The Birdie table does not exist in the database.")

if __name__ == '__main__':
    with app.app_context():
        init_db()
        verify_db()