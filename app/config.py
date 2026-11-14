import ipaddress
import logging
import os
import sys
import time
from functools import cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import praw
import prawcore

from app import __version__, __author__

logger = logging.getLogger(__name__)

DEFAULT_CUTOFF_HOURS = 24
DEFAULT_REFRESH_MINUTES = 60
# A year and a day, far below the values whose date arithmetic overflows and stops updates
MAX_CUTOFF_HOURS = 8760
MAX_REFRESH_MINUTES = 1440
REQUIRED_VARS = ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET")


class SettingError(ValueError):
    """A setting has a value the app can't use."""


def _setting(name):
    """The variable's value, or None when it's unset or empty, so an empty value gets the default."""
    return os.getenv(name, "").strip() or None


def _whole_number(name, default, maximum, minimum=1):
    value = _setting(name)
    if value is None:
        return default
    try:
        number = int(value)
    except ValueError:
        raise SettingError(f"{name} must be a whole number, got '{value}'.") from None
    if not minimum <= number <= maximum:
        raise SettingError(f"{name} must be from {minimum} to {maximum}, got {number}.")
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
    return _whole_number("THREAD_TTL_HOURS", DEFAULT_CUTOFF_HOURS, MAX_CUTOFF_HOURS)


@cache
def get_refresh_minutes():
    return _whole_number("SCHEDULER_INTERVAL_MINUTES", DEFAULT_REFRESH_MINUTES, MAX_REFRESH_MINUTES)


@cache
def get_time_zone():
    """The zone for dates in the web UI. An unknown TZ only affects displayed times, so it falls back to UTC."""
    name = _setting("TZ")
    unknown = False
    try:
        zone = ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        unknown = True
        zone = ZoneInfo("UTC")
    # APScheduler and the log timestamps read TZ itself, unstripped, and APScheduler stops on a zone it can't
    # read, so they get the zone the app uses
    os.environ["TZ"] = zone.key
    time.tzset()
    if unknown:
        logger.warning(f"TZ '{name}' isn't a known time zone name, such as America/New_York. Using UTC.")
    return zone


def get_forwarded_allow_ips():
    """uvicorn reads FORWARDED_ALLOW_IPS itself and quietly trusts no proxy for an entry it can't parse.

    entrypoint.sh removes every space and tab first, as this check ignores them, so both see the same value.
    """
    value = _setting("FORWARDED_ALLOW_IPS")
    if value is None or value == "*":
        return value
    for entry in filter(None, (part.strip() for part in value.split(","))):
        try:
            # uvicorn's own parsing: a network with host bits set, such as 10.0.0.5/24, isn't one
            ipaddress.ip_network(entry) if "/" in entry else ipaddress.ip_address(entry)
        except ValueError:
            which = "" if entry == value else f" ('{entry}' isn't one)"
            raise SettingError(
                f"FORWARDED_ALLOW_IPS must be * on its own, or IP addresses and networks separated by commas, "
                f"got '{value}'{which}."
            ) from None
    return value


def check_reddit_login():
    """Ask Reddit for a token once, so wrong credentials stop the app instead of failing every update."""
    try:
        get_reddit_client().auth.scopes()
    except (prawcore.exceptions.OAuthException, prawcore.exceptions.ResponseException) as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if isinstance(e, prawcore.exceptions.OAuthException) or status == 401:
            raise SettingError(
                "Reddit rejected REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET. "
                "Check both against the app at reddit.com/prefs/apps."
            ) from None
        logger.warning(f"Couldn't check the Reddit credentials ({e}). Starting anyway.")
    except prawcore.exceptions.RequestException as e:
        reason = type(e.original_exception).__name__
        logger.warning(f"Couldn't reach Reddit to check the credentials ({reason}). Starting anyway.")


def check_settings():
    """Read every setting once at startup, so a bad value stops the app here instead of failing later."""
    problems = []
    reads = (
        get_time_zone,
        get_reddit_credentials,
        get_active_hours,
        get_refresh_minutes,
        get_forwarded_allow_ips,
    )
    for read in reads:
        try:
            read()
        except SettingError as e:
            problems.append(str(e))
    # Only with every other setting usable: the check calls Reddit
    if not problems:
        try:
            check_reddit_login()
        except SettingError as e:
            problems.append(str(e))
    for problem in problems:
        logger.error(problem)
    if problems:
        sys.exit(1)


def get_database_url():
    return "sqlite:///./data/data.db"
