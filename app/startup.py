import os
import sys
from datetime import datetime, timezone

from app.config import get_refresh_minutes
from app.threads.backfill import backfill_missing_threads, fetch_missing_threads


def resolve_backfill_date(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    if value.lower() == "auto":
        auto = datetime(datetime.now(timezone.utc).year, 2, 1, tzinfo=timezone.utc)
        print(f"[STARTUP] BACKFILL_DATE=auto resolved to {auto.strftime('%Y-%m-%d')}.")
        return auto.timestamp()
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        print(f"[ERROR] BACKFILL_DATE '{value}' is not valid. Use YYYY-MM-DD or 'auto'.")
        sys.exit(1)


def run_backfill(cutoff: float):
    missing = backfill_missing_threads(cutoff)
    if missing:
        print(f"[STARTUP] Fetching {len(missing)} missing thread(s)...")
        fetch_missing_threads(missing)
    else:
        print("[STARTUP] No missing threads found. Backfill complete.")


# Run with: pipenv run python -m app.startup
# Docker scheduler service entry point -- optionally runs backfill then starts the scheduler.
# Set BACKFILL_DATE=auto or BACKFILL_DATE=YYYY-MM-DD to enable backfill on startup.
if __name__ == "__main__":
    from apscheduler.schedulers.blocking import BlockingScheduler
    from app.threads.fetch_active import deactivate_old_threads, fetch_active_threads, fetch_new_threads

    backfill_env = os.getenv("BACKFILL_DATE", "").strip()

    if backfill_env:
        cutoff = resolve_backfill_date(backfill_env)
        print(f"[STARTUP] Running backfill before starting scheduler...")
        run_backfill(cutoff)
        print("[STARTUP] Backfill finished. Starting scheduler.")
    else:
        print("[STARTUP] BACKFILL_DATE not set. Skipping backfill.")

    scheduler = BlockingScheduler()

    def update_threads():
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone()
        timestamp = f"{now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC ({now_local.strftime('%-I:%M %p')})"
        print(f"[SCHEDULER] Updating threads at {timestamp}.")
        deactivate_old_threads()
        fetch_active_threads()
        fetch_new_threads()

    @scheduler.scheduled_job('interval', minutes=get_refresh_minutes())
    def scheduled_update():
        update_threads()

    print(f"[SCHEDULER] First run will occur immediately, then every {get_refresh_minutes()} minute(s).")
    update_threads()
    scheduler.start()
