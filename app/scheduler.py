from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timezone

from app.config import get_refresh_minutes
from app.threads.fetch_active import deactivate_old_threads, fetch_active_threads, fetch_new_threads

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

# run with: pipenv run python -m app.scheduler
if __name__ == "__main__":
    print(f"[SCHEDULER] First run will occur immediately, then every {get_refresh_minutes()} minute(s).")
    update_threads()
    scheduler.start()
