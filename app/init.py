# app/init.py
from app.db import init_db

# run with pipenv run python -m app.init
if __name__ == "__main__":
    init_db()
    print("Database initialized.")
