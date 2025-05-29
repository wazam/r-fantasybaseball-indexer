from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_database_url
from app.models import Base

DATABASE_URL = get_database_url()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
