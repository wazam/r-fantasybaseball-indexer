import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app.config import REFRESH_MINUTES, check_settings
from app.db import check_data_folder, init_db
from app.threads.deleted_authors import relabel_deleted_authors_once
from app.threads.fetch_active import deactivate_old_threads, fetch_active_threads, fetch_new_threads
from app.threads.reply_counts import recount_replies_once
from app.web.routes import router, static_version

logger = logging.getLogger(__name__)

# Runs when uvicorn imports this module: a bad setting or an unwritable data folder stops the app before anything
# starts
check_settings()
check_data_folder()


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

    # The first update runs now and, after downtime, fills the gap since the newest stored thread
    scheduler.add_job(update_threads, "interval", minutes=REFRESH_MINUTES, next_run_time=datetime.now())
    scheduler.start()
    logger.info(f"Updates will run every {REFRESH_MINUTES} minutes.")

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
