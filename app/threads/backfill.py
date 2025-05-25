import sys

from app.db import SessionLocal
from app.models import Thread
from app.reddit import fetch_and_store_thread
from app.threads.search import get_thread_urls

def backfill_missing_threads():
    missing_urls = []
    urls = get_thread_urls(only_active=False)

    print(f"\n[INFO] Checking {len(urls)} potential threads...")

    with SessionLocal() as session:
        for url in urls:
            exists = session.query(Thread).filter_by(permalink=url).first()
            if exists:
                print(f"[OK] Already in DB: {url}")
            else:
                print(f"[X] Missing: {url}")
                missing_urls.append(url)

    print(f"\n[INFO] Found {len(missing_urls)} missing threads.\n")
    return missing_urls

def fetch_missing_threads(missing_urls):
    for i, url in enumerate(missing_urls, 1):
        print(f"[FETCH] {i} of {len(missing_urls)}:\n{url}")
        fetch_and_store_thread(url, assume_active=False)
    print(f"[DONE] Backfill complete — {len(missing_urls)} thread(s) fetched.")

# Run with: pipenv run python -m app.threads.backfill [--fetch]
if __name__ == "__main__":
    do_fetch = "--fetch" in sys.argv

    print("[BACKFILL] Starting thread backfill check...")
    missing = backfill_missing_threads()

    if do_fetch and missing:
        print("[BACKFILL] Fetching and storing missing threads...")
        fetch_missing_threads(missing)
    elif not do_fetch:
        print("[INFO] Run with '--fetch' to fetch and store missing threads.")
    elif do_fetch and not missing:
        print("[OK] All threads already stored. No fetch needed.")
