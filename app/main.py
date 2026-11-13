import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app.config import check_settings, get_backfill_cutoff, get_refresh_minutes
from app.db import init_db
from app.threads.backfill import backfill_missing_threads, fetch_missing_threads
from app.threads.deleted_authors import relabel_deleted_authors_once
from app.threads.fetch_active import deactivate_old_threads, fetch_active_threads, fetch_new_threads
from app.threads.reply_counts import recount_replies_once
from app.web.routes import router, static_version

logger = logging.getLogger(__name__)

# Runs when uvicorn imports this module: a bad setting stops the app before anything starts
check_settings()


def run_backfill(cutoff: float):
    missing = backfill_missing_threads(cutoff)
    if missing:
        logger.info(f"Fetching {len(missing)} missing thread(s)...")
        fetch_missing_threads(missing)
    else:
        logger.info("No missing threads found. Backfill complete.")


def update_threads():
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone()
    timestamp = f"{now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC ({now_local.strftime('%-I:%M %p')})"
    logger.info(f"Updating threads at {timestamp}.")
    deactivate_old_threads()
    fetch_active_threads()
    fetch_new_threads()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recount_replies_once()
    relabel_deleted_authors_once()

    scheduler = BackgroundScheduler()

    cutoff = get_backfill_cutoff()
    if cutoff is not None:
        logger.info("BACKFILL_DATE set. Backfill will run before the first scheduled update.")

        def run_backfill_then_start_interval():
            logger.info("Running backfill...")
            run_backfill(cutoff)
            logger.info("Backfill finished. Starting recurring updates.")
            update_threads()
            scheduler.add_job(update_threads, "interval", minutes=get_refresh_minutes())

        scheduler.add_job(run_backfill_then_start_interval)
    else:
        logger.info("BACKFILL_DATE not set. Skipping backfill.")
        scheduler.add_job(update_threads, "interval", minutes=get_refresh_minutes(), next_run_time=datetime.now())

    scheduler.start()
    logger.info(f"Updates will run every {get_refresh_minutes()} minute(s).")

    yield

    scheduler.shutdown()


app = FastAPI(title="Anything Goes Archive", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)

templates = Jinja2Templates(directory="app/web/templates")
templates.env.globals["static_version"] = static_version


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "404.html", status_code=404)
