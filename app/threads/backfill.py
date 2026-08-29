import argparse
import logging
import sys
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import Thread
from app.reddit import fetch_and_store_thread
from app.threads.search import get_thread_urls

logger = logging.getLogger(__name__)


def backfill_missing_threads(cutoff_date: float):
    missing_urls = []
    urls = get_thread_urls(only_active=False, cutoff_date=cutoff_date)

    logger.info(f"Checking {len(urls)} potential threads.")

    with SessionLocal() as session:
        for url in urls:
            exists = session.query(Thread).filter_by(permalink=url).first()
            if exists:
                logger.info(f"Skipping already archived thread: {url}")
            else:
                logger.info(f"Found new missing thread: {url}")
                missing_urls.append(url)

    logger.info(f"Found {len(missing_urls)} missing threads.")
    return missing_urls


def fetch_missing_threads(missing_urls):
    for i, url in enumerate(missing_urls, 1):
        logger.info(f"Fetching {i} of {len(missing_urls)}: {url}")
        fetch_and_store_thread(url)
    logger.info(f"Backfill complete. {len(missing_urls)} thread(s) fetched.")


# Run with: pipenv run python -m app.threads.backfill 2026-02-10
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Backfill missing Anything Goes threads.")
    parser.add_argument("date", help="Cutoff date in YYYY-MM-DD format (e.g. 2026-02-10)")
    args = parser.parse_args()

    try:
        cutoff = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        logger.error("Date must be in YYYY-MM-DD format.")
        sys.exit(1)

    logger.info(f"Starting backfill from {args.date}...")
    missing = backfill_missing_threads(cutoff)

    if missing:
        logger.info("Fetching and storing missing threads...")
        fetch_missing_threads(missing)
    else:
        logger.info("All threads already stored. No fetch needed.")
