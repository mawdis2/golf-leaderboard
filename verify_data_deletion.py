# verify_data_deletion.py
from sqlalchemy import create_engine, inspect

def verify_data_deletion():
    engine = create_engine('sqlite:///golf_leaderboard.db')
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables in the database: {tables}")
    for table in tables:
        row_count = engine.execute(f"SELECT COUNT(*) FROM {table}").scalar()
        print(f"Table {table} has {row_count} rows.")

if __name__ == "__main__":
    verify_data_deletion()