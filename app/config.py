import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import praw

from app import __version__, __author__

load_dotenv()

DEFAULT_CUTOFF_DATE = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")  # 7 days
DEFAULT_CUTOFF_HOURS = 24
DEFAULT_REFRESH_MINUTES = 60

def get_reddit_client():
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("[ERROR] Missing Reddit API credentials. Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your .env file.")

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=os.getenv(
            "REDDIT_USER_AGENT",
            f"linux:r-fantasybaseball-indexer:v{__version__} (by /u/{__author__})"
        )
    )

def get_cutoff_date():
    cutoff_str = os.getenv("THREAD_BACKFILL_CUTOFF_DATE", DEFAULT_CUTOFF_DATE)
    try:
        return datetime.strptime(cutoff_str, "%Y-%m-%d").timestamp()
    except ValueError:
        raise ValueError("[ERROR] THREAD_BACKFILL_CUTOFF_DATE must be in YYYY-MM-DD format.")

def get_active_hours():
    try:
        return int(os.getenv("THREAD_ACTIVE_CUTOFF_HOURS", DEFAULT_CUTOFF_HOURS))
    except ValueError:
        raise ValueError("[ERROR] THREAD_ACTIVE_CUTOFF_HOURS must be an integer.")

def get_refresh_minutes():
    try:
        return int(os.getenv("THREAD_REFRESH_RATE_MINUTES", DEFAULT_REFRESH_MINUTES))
    except ValueError:
        raise ValueError("[ERROR] THREAD_REFRESH_RATE_MINUTES must be an integer.")

def get_database_url():
    return os.getenv("DATABASE_URL", "sqlite:///./data.db")
