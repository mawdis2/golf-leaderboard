# verify_db.py
from sqlalchemy import create_engine, inspect

def verify_db():
    engine = create_engine('sqlite:///golf_leaderboard.db')
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables in the database: {tables}")
    if 'Birdie' in tables:
        columns = inspector.get_columns('Birdie')
        print(f"Columns in the Birdie table: {columns}")
    else:
        print("The Birdie table does not exist in the database.")

if __name__ == "__main__":
    verify_db()