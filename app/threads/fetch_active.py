from datetime import datetime, timedelta, UTC
import logging

from app.config import get_active_hours
from app.db import SessionLocal
from app.models import Thread
from app.reddit import fetch_and_store_thread
from app.threads.search import get_thread_urls

logger = logging.getLogger(__name__)

def deactivate_old_threads():
    cutoff = datetime.now(UTC) - timedelta(hours=get_active_hours())

    with SessionLocal() as session:
        updated = session.query(Thread).filter(
            Thread.is_active == True,
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
        active_threads = session.query(Thread).filter(Thread.is_active == True).all()

    if not active_threads:
        logger.info("No active threads to update.")
        return

    logger.info(f"Found {len(active_threads)} active thread(s) to update.")

    for i, thread in enumerate(active_threads, 1):
        logger.info(f"Fetching thread {i}/{len(active_threads)}: {thread.permalink}")
        fetch_and_store_thread(thread.permalink)

    logger.info(f"Updated {len(active_threads)} active thread(s).")

def fetch_new_threads():
    recent_urls = get_thread_urls()
    added = 0

    with SessionLocal() as session:
        for url in recent_urls:
            exists = session.query(Thread).filter_by(permalink=url).first()
            if exists:
                continue  # Skip silently to reduce log spam

            logger.info(f"Fetching newly posted thread: {url}")
            fetch_and_store_thread(url)
            added += 1

    logger.info(f"Fetched {added} new thread(s).")

# Run with: pipenv run python -m app.threads.fetch_active
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")

    # logger.info("Manually overriding all threads as active.")
    # activate_all_threads()

    logger.info("Checking for outdated threads.")
    deactivate_old_threads()

    logger.info("Fetching updates for threads.")
    fetch_active_threads()

    logger.info("Checking for new threads.")
    fetch_new_threads()
    logger.info("Threads fetched and updated successfully.")
