import argparse
import logging
import sys
from datetime import datetime, timezone

from app.config import check_settings
from app.db import check_data_folder
from app.threads.fetch_active import fetch_threads_since

logger = logging.getLogger(__name__)

# Imports threads older than the updates reach on their own, which is the newest stored thread or a week back
# Run with: docker exec anything-goes-archive ./.venv/bin/python -m app.threads.backfill 2026-02-10
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
    check_settings()
    check_data_folder()

    parser = argparse.ArgumentParser(description="Backfill missing Anything Goes threads.")
    parser.add_argument("date", help="Cutoff date in YYYY-MM-DD format (e.g. 2026-02-10)")
    args = parser.parse_args()

    try:
        cutoff = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        logger.error("Date must be in YYYY-MM-DD format.")
        sys.exit(1)

    logger.info(f"Backfilling threads posted since {args.date}.")
    fetch_threads_since(cutoff)
