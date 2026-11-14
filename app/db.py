import logging
import os
import sys
import tempfile

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_database_url
from app.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = get_database_url()
# The folder that holds data.db and SQLite's journal files, the only things the app writes
DATA_FOLDER = os.path.dirname(os.path.abspath(DATABASE_URL.removeprefix("sqlite:///")))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    # create_all() only creates missing tables, so a database that already had
    # the comments table before the author column was indexed needs this run
    # explicitly too. Safe to run on every startup either way.
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comments_author ON comments(author)"))


def check_data_folder():
    """Stop the app with the fix if the data folder can't be written, e.g. a root-owned ./data that Docker
    created. Otherwise it fails later with SQLite's own error."""
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
        with tempfile.TemporaryFile(dir=DATA_FOLDER):
            pass
    except OSError as error:
        uid, gid = os.getuid(), os.getgid()
        logger.error(
            f"Can't write to {DATA_FOLDER} ({error.strerror}). The app runs as {uid}:{gid}, so on the host, give "
            f"the data folder next to compose.yaml to that user: sudo chown -R {uid}:{gid} ./data. Or, if the "
            f"folder belongs to another user, set user: in compose.yaml to the owner shown by: ls -nd ./data"
        )
        sys.exit(1)
