# inspect_dates_sql.py
from sqlalchemy import create_engine, text

def inspect_dates():
    engine = create_engine('sqlite:///golf_leaderboard.db')
    with engine.connect() as connection:
        result = connection.execute(text("SELECT id, date FROM Birdie"))
        for row in result:
            print(f"Birdie ID: {row['id']}, Date: {row['date']}, Type: {type(row['date'])}")

if __name__ == "__main__":
    inspect_dates()