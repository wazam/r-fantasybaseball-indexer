from app.db import init_db

# run with: pipenv run python -m app.init
if __name__ == "__main__":
    print("[INIT] Initializing database.")
    try:
        init_db()
        print("[DONE] Database initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
