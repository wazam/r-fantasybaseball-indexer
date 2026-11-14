from datetime import datetime, timedelta, UTC
import logging

from sqlalchemy import func

from app.config import ACTIVE_HOURS, check_settings
from app.db import SessionLocal, check_data_folder
from app.models import Thread
from app.reddit import fetch_and_store_thread
from app.threads.search import LOOKBACK_DAYS, get_thread_urls

logger = logging.getLogger(__name__)


def deactivate_old_threads():
    cutoff = datetime.now(UTC) - timedelta(hours=ACTIVE_HOURS)

    with SessionLocal() as session:
        updated = session.query(Thread).filter(
            Thread.is_active == True,  # noqa: E712 (SQLAlchemy needs ==)
            Thread.posted_at < cutoff
        ).update({
            Thread.is_active: False,
            Thread.last_saved: datetime.now(UTC)
        })
        session.commit()

    logger.info(f"Marked {updated} thread(s) as inactive.")


def activate_all_threads():
    with SessionLocal() as session:
        updated = session.query(Thread).update({
            Thread.is_active: True,
            Thread.last_saved: datetime.now(UTC)
        })
        session.commit()

    logger.info(f"Marked {updated} thread(s) as active.")


def fetch_active_threads():
    with SessionLocal() as session:
        active_threads = session.query(Thread).filter(Thread.is_active == True).all()  # noqa: E712 (SQLAlchemy needs ==)

    if not active_threads:
        logger.info("No active threads to update.")
        return

    logger.info(f"Found {len(active_threads)} active thread(s) to update.")

    for i, thread in enumerate(active_threads, 1):
        logger.info(f"Fetching thread {i}/{len(active_threads)}: {thread.permalink}")
        fetch_and_store_thread(thread.permalink)

    logger.info(f"Updated {len(active_threads)} active thread(s).")


def lookback_cutoff():
    """Where the search for missing threads starts: the newest stored thread or LOOKBACK_DAYS ago, whichever is
    earlier, so the first update after downtime fills the gap."""
    lookback = datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)
    with SessionLocal() as session:
        newest = session.query(func.max(Thread.posted_at)).scalar()
    if newest is not None:
        # SQLite stores the UTC time without its zone
        newest = newest.replace(tzinfo=UTC)
        if newest < lookback:
            logger.info(f"The newest stored thread is from {newest:%Y-%m-%d}. Looking for threads missed since then.")
            return newest.timestamp()
    return lookback.timestamp()


def fetch_threads_since(cutoff: float):
    """Fetch every thread posted since cutoff, a UTC timestamp, that isn't stored yet."""
    with SessionLocal() as session:
        missing = [url for url in get_thread_urls(cutoff) if not session.query(Thread).filter_by(permalink=url).first()]

    # Oldest first: if the app stops partway, the newest stored thread marks where to carry on
    missing.reverse()
    for i, url in enumerate(missing, 1):
        logger.info(f"Fetching missing thread {i}/{len(missing)}: {url}")
        fetch_and_store_thread(url)

    logger.info(f"Fetched {len(missing)} new thread(s).")


def fetch_new_threads():
    fetch_threads_since(lookback_cutoff())


# Run with: docker exec anything-goes-archive ./.venv/bin/python -m app.threads.fetch_active
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
    check_settings()
    check_data_folder()

    # logger.info("Manually overriding all threads as active.")
    # activate_all_threads()

    logger.info("Checking for outdated threads.")
    deactivate_old_threads()

    logger.info("Fetching updates for threads.")
    fetch_active_threads()

    logger.info("Checking for new threads.")
    fetch_new_threads()
    logger.info("Threads fetched and updated successfully.")
