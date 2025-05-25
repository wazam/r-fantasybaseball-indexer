from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Thread(Base):
    __tablename__ = 'threads'

    id = Column(Integer, primary_key=True, index=True)  # internal DB ID
    reddit_id = Column(String, unique=True, nullable=False, index=True)  # e.g., "1ksagtd"

    title = Column(String, nullable=False)
    permalink = Column(String, nullable=False)

    score = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=False)

    posted_at = Column(DateTime, nullable=False, index=True)
    first_saved = Column(DateTime, default=func.now(), nullable=False)
    last_saved = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    comments = relationship("Comment", back_populates="thread")

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(String, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)

    parent_id = Column(String, nullable=True)  # NULL if top-level comment
    body = Column(Text, nullable=False)
    author = Column(String, nullable=False)
    flair = Column(String, nullable=True)  # NULL if unset
    permalink = Column(String, nullable=False)

    score = Column(Integer, default=0, nullable=False)
    replies_direct = Column(Integer, default=0, nullable=False)
    replies_all = Column(Integer, default=0, nullable=False)

    created_utc = Column(DateTime, nullable=False, index=True)
    first_saved = Column(DateTime, default=func.now(), nullable=False)
    last_saved = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    thread = relationship("Thread", back_populates="comments")
