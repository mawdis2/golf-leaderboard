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
from sqlalchemy import text, inspect, MetaData, Table, Column, String
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
        
        # Create alembic_version table first
        print("  -> Creating alembic_version table...")
        metadata = MetaData()
        alembic_version = Table(
            'alembic_version',
            metadata,
            Column('version_num', String(32), nullable=False),
            schema='public'
        )
        metadata.create_all(bind=db.engine)
        
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
from sqlalchemy import engine_from_config, pool, MetaData, Table, Column, String
from alembic import context
from app import app, db
from models import Player, Course, Birdie, HistoricalTotal

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = db.metadata

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        # Always include tables in the autogenerate
        return True
    return False

def process_revision_directives(context, revision, directives):
    if directives[0].upgrade_ops.ops:
        # Ensure tables are dropped in correct order
        directives[0].upgrade_ops.ops.sort(
            key=lambda op: (
                # Drop dependent tables first
                -1 if op.__class__.__name__ == "DropTableOp" and op.table_name in ["birdie", "historical_total"] else
                # Then drop base tables
                0 if op.__class__.__name__ == "DropTableOp" and op.table_name in ["player", "course"] else
                # Create base tables first
                1 if op.__class__.__name__ == "CreateTableOp" and op.table_name in ["player", "course"] else
                # Create dependent tables last
                2
            )
        )

def run_migrations_offline():
    url = app.config['SQLALCHEMY_DATABASE_URI']
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        include_schemas=True,
        version_table_schema="public"
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # Create alembic_version table if it doesn't exist
    with app.app_context():
        with db.engine.connect() as connection:
            if not db.inspect(db.engine).has_table("alembic_version", schema="public"):
                metadata = MetaData()
                Table(
                    'alembic_version',
                    metadata,
                    Column('version_num', String(32), nullable=False),
                    schema='public'
                )
                metadata.create_all(bind=connection)

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
            include_object=include_object,
            process_revision_directives=process_revision_directives,
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