from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_database_url
from app.models import Base

DATABASE_URL = get_database_url()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # create_all() only creates missing tables, so a database that already had
    # the comments table before the author column was indexed needs this run
    # explicitly too. Safe to run on every startup either way.
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comments_author ON comments(author)"))
