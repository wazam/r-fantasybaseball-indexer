import os
from dotenv import load_dotenv
import praw

from app import __version__, __author__

load_dotenv()

DEFAULT_CUTOFF_HOURS = 24
DEFAULT_REFRESH_MINUTES = 60


def get_reddit_client():
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("[ERROR] Missing Reddit API credentials. Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your .env file.")

    default_user_agent = f"linux:r-fantasybaseball-indexer:v{__version__} (by /u/{__author__})"

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        # compose.yaml passes an empty string when REDDIT_USER_AGENT is unset
        user_agent=os.getenv("REDDIT_USER_AGENT") or default_user_agent,
    )


def get_active_hours():
    try:
        return int(os.getenv("THREAD_TTL_HOURS", DEFAULT_CUTOFF_HOURS))
    except ValueError:
        raise ValueError("[ERROR] THREAD_TTL_HOURS must be an integer.")


def get_refresh_minutes():
    try:
        return int(os.getenv("SCHEDULER_INTERVAL_MINUTES", DEFAULT_REFRESH_MINUTES))
    except ValueError:
        raise ValueError("[ERROR] SCHEDULER_INTERVAL_MINUTES must be an integer.")


def get_database_url():
    return "sqlite:///./data/data.db"
