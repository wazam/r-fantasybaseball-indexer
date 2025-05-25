from datetime import datetime, timedelta, UTC

from app.config import get_cutoff_hours
from app.db import SessionLocal
from app.models import Thread
from app.reddit import fetch_and_store_thread

def deactivate_old_threads():
    cutoff = datetime.now(UTC) - timedelta(hours=get_cutoff_hours())

    with SessionLocal() as session:
        updated = session.query(Thread).filter(
            Thread.is_active == True,
            Thread.posted_at < cutoff
        ).update({
            Thread.is_active: False,
            Thread.last_saved: datetime.now(UTC)
        })
        session.commit()

    print(f"[INFO] Marked {updated} thread(s) as inactive.")

def activate_all_threads():
    with SessionLocal() as session:
        updated = session.query(Thread).update({
            Thread.is_active: True,
            Thread.last_saved: datetime.now(UTC)
        })
        session.commit()

    print(f"[INFO] Marked {updated} thread(s) as active.")

def fetch_active_threads():
    with SessionLocal() as session:
        active_threads = session.query(Thread).filter(Thread.is_active == True).all()

    if not active_threads:
        print("[WARN] No active threads to update.")
        return

    print(f"[INFO] Found {len(active_threads)} active thread(s) to update.")

    for i, thread in enumerate(active_threads, 1):
        print(f"[FETCH] ({i}/{len(active_threads)}) Updating: {thread.permalink}")
        fetch_and_store_thread(thread.permalink, assume_active=True)

    print(f"[DONE] Refreshed {len(active_threads)} active thread(s).")

# Run with: pipenv run python -m app.threads.fetch_active
if __name__ == "__main__":
    print("[FETCH_ACTIVE] Checking for outdated threads based on THREAD_ACTIVE_CUTOFF_HOURS...")
    deactivate_old_threads()

    # activate_all_threads()  # uncomment to force-reactivate all threads (for testing)
    # print("[FETCH_ACTIVE] All threads manually reactivated.")
    
    print("[FETCH_ACTIVE] Fetching updates for active threads...")
    fetch_active_threads()
