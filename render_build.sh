#!/usr/bin/env bash
# Exit on error
set -e

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=production
export PYTHONPATH=$PYTHONPATH:/opt/render/project/src

# Install dependencies
echo "==> Installing dependencies..."
python -m pip install --no-cache-dir -r requirements.txt

# Create database initialization script
cat > init_db.py << 'EOF'
import os, sys, time
from sqlalchemy import text, inspect, MetaData
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

start_time = time.time()
print("==> Starting database initialization...")

from app import app, db
from models import Player, Course, Birdie, HistoricalTotal

def verify_table_exists(table_name):
    with db.engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :table)"
        ), {"table": table_name})
        return result.scalar()

with app.app_context():
    try:
        print(f"  -> Database URL: {db.engine.url}")
        print("  -> Testing database connection...")
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("  -> Database connection successful")

        # First transaction: Schema setup with CASCADE
        print("  -> Setting up schema...")
        with db.engine.connect() as conn:
            conn.execute(text('COMMIT'))  # Close any existing transaction
            conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
            conn.execute(text('CREATE SCHEMA public'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
            conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
            conn.execute(text('COMMIT'))
        
        print("  -> Verifying models...")
        models = [Player, Course, Birdie, HistoricalTotal]
        for model in models:
            print(f"    - Registering model: {model.__name__}")
            if not hasattr(model, '__table__'):
                raise Exception(f"Model {model.__name__} has no __table__ attribute")
            print(f"      Table name: {model.__table__.name}")
            print(f"      Columns: {', '.join(c.name for c in model.__table__.columns)}")
        
        print("  -> Creating tables in dependency order...")
        with db.engine.begin() as conn:
            # First create tables without foreign keys
            for model in [Player, Course]:
                print(f"    - Creating base table: {model.__table__.name}")
                model.__table__.create(bind=conn)
            
            # Then create tables with foreign keys
            for model in [Birdie, HistoricalTotal]:
                print(f"    - Creating dependent table: {model.__table__.name}")
                model.__table__.create(bind=conn)
        
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
        tables = ['player', 'course', 'birdie', 'historical_total']
        existing_tables = inspector.get_table_names()
        print(f"    - Found tables: {existing_tables}")
        
        for table in tables:
            if not table in existing_tables:
                raise Exception(f"Table {table} was not created successfully")
            columns = [c['name'] for c in inspector.get_columns(table)]
            fks = inspector.get_foreign_keys(table)
            print(f"    - Verified table {table}:")
            print(f"      Columns: {columns}")
            if fks:
                print(f"      Foreign keys: {[fk['referred_table'] for fk in fks]}")
            
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

# Create migration script
cat > migration_env.py << 'EOF'
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app import app, db

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = db.metadata

def run_migrations_offline():
    url = app.config['SQLALCHEMY_DATABASE_URI']
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = app.config["SQLALCHEMY_DATABASE_URI"]
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
            version_table_schema="public"
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF

# Remove existing migrations
echo "==> Cleaning up old migrations..."
rm -rf migrations

# Initialize fresh migrations
echo "==> Setting up fresh migrations..."
flask db init

# Replace env.py with our custom version
mv migration_env.py migrations/env.py

# Create initial migration
echo "==> Creating initial migration..."
flask db migrate -m "Initial migration"

# Apply migration
echo "==> Applying migration..."
flask db upgrade

# Verify final state
echo "==> Verifying final database state..."
python -c "
from app import app, db
from sqlalchemy import inspect
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print('Available tables:', tables)
    for table in tables:
        columns = [c['name'] for c in inspector.get_columns(table)]
        fks = inspector.get_foreign_keys(table)
        print(f'Table {table}:')
        print(f'  Columns: {columns}')
        if fks:
            print(f'  Foreign keys: {[fk[\"referred_table\"] for fk in fks]}')
    
    # Verify tables exist and are accessible
    from models import Player, Course, Birdie, HistoricalTotal
    for model in [Player, Course, Birdie, HistoricalTotal]:
        try:
            count = model.query.count()
            print(f'{model.__name__} table is accessible (count: {count})')
        except Exception as e:
            print(f'Error accessing {model.__name__} table: {e}')
            raise
"

# Clean up
rm -f init_db.py 