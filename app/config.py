import logging
import os
import sys
import time
from datetime import datetime, timezone
from functools import cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import praw

from app import __version__, __author__

logger = logging.getLogger(__name__)

DEFAULT_CUTOFF_HOURS = 24
DEFAULT_REFRESH_MINUTES = 60
REQUIRED_VARS = ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET")


class SettingError(ValueError):
    """A setting has a value the app can't use."""


def _setting(name):
    """The variable's value, or None when it's unset or empty, so an empty value gets the default."""
    return os.getenv(name, "").strip() or None


def _whole_number(name, default, minimum=1):
    value = _setting(name)
    if value is None:
        return default
    try:
        number = int(value)
    except ValueError:
        raise SettingError(f"{name} must be a whole number, got '{value}'.") from None
    if number < minimum:
        raise SettingError(f"{name} must be at least {minimum}, got {number}.")
    return number


def get_reddit_credentials():
    missing = [name for name in REQUIRED_VARS if _setting(name) is None]
    if missing:
        one = len(missing) == 1
        raise SettingError(
            f"Missing or empty required {'variable' if one else 'variables'}: {', '.join(missing)}. "
            f"Set {'it' if one else 'them'} in .env, or in the deployed stack's environment."
        )
    return _setting("REDDIT_CLIENT_ID"), _setting("REDDIT_CLIENT_SECRET")


@cache
def get_reddit_client():
    """One client, created on first use, so importing a module never needs the credentials."""
    client_id, client_secret = get_reddit_credentials()
    default_user_agent = f"linux:r-fantasybaseball-indexer:v{__version__} (by /u/{__author__})"
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=_setting("REDDIT_USER_AGENT") or default_user_agent,
    )


@cache
def get_active_hours():
    return _whole_number("THREAD_TTL_HOURS", DEFAULT_CUTOFF_HOURS)


@cache
def get_refresh_minutes():
    return _whole_number("SCHEDULER_INTERVAL_MINUTES", DEFAULT_REFRESH_MINUTES)


@cache
def get_backfill_cutoff():
    """The BACKFILL_DATE cutoff as a UTC timestamp, or None when it's unset."""
    value = _setting("BACKFILL_DATE")
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        raise SettingError(f"BACKFILL_DATE must be a YYYY-MM-DD date, got '{value}'.") from None


@cache
def get_time_zone():
    """The zone for dates in the web UI. An unknown TZ only affects displayed times, so it falls back to UTC."""
    name = _setting("TZ")
    if name is None:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(f"TZ '{name}' isn't a known time zone. Using UTC.")
        # APScheduler reads TZ itself and stops on an unknown zone, and the log timestamps should agree
        os.environ["TZ"] = "UTC"
        time.tzset()
        return ZoneInfo("UTC")


def check_settings():
    """Read every setting once at startup, so a bad value stops the app here instead of failing later."""
    problems = []
    for read in (get_reddit_credentials, get_active_hours, get_refresh_minutes, get_backfill_cutoff, get_time_zone):
        try:
            read()
        except SettingError as e:
            problems.append(str(e))
    for problem in problems:
        logger.error(problem)
    if problems:
        sys.exit(1)


def get_database_url():
    return "sqlite:///./data/data.db"
