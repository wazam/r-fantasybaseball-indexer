import argparse
import sys
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import Thread
from app.reddit import fetch_and_store_thread
from app.threads.search import get_thread_urls


def backfill_missing_threads(cutoff_date: float):
    missing_urls = []
    urls = get_thread_urls(only_active=False, cutoff_date=cutoff_date)

    print(f"[INFO] Checking {len(urls)} potential threads.\n")

    with SessionLocal() as session:
        for url in urls:
            exists = session.query(Thread).filter_by(permalink=url).first()
            if exists:
                print(f"[INFO] Skipping already archived thread: {url}")
            else:
                print(f"[INFO] Found new missing thread: {url}")
                missing_urls.append(url)

    print(f"\n[INFO] Found {len(missing_urls)} missing threads.")
    return missing_urls


def fetch_missing_threads(missing_urls):
    for i, url in enumerate(missing_urls, 1):
        print(f"[INFO] Fetching {i} of {len(missing_urls)}: {url}")
        fetch_and_store_thread(url)
    print(f"[INFO] Backfill complete. {len(missing_urls)} thread(s) fetched.")


# Run with: pipenv run python -m app.threads.backfill 2026-02-10
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill missing Anything Goes threads.")
    parser.add_argument("date", help="Cutoff date in YYYY-MM-DD format (e.g. 2026-02-10)")
    args = parser.parse_args()

    try:
        cutoff = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        print("[ERROR] Date must be in YYYY-MM-DD format.")
        sys.exit(1)

    print(f"[BACKFILL] Starting backfill from {args.date}...")
    missing = backfill_missing_threads(cutoff)

    if missing:
        print("[INFO] Fetching and storing missing threads...")
        fetch_missing_threads(missing)
    else:
        print("[INFO] All threads already stored. No fetch needed.")
