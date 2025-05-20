# app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Thread(Base):
    __tablename__ = 'threads'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

    comments = relationship("Comment", back_populates="thread")

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(String, primary_key=True)  # Reddit ID (e.g., 'gk1234')
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    parent_id = Column(String, nullable=True)  # None if top-level comment
    body = Column(Text, nullable=False)
    author = Column(String, nullable=False)
    flair = Column(String, nullable=True)
    score = Column(Integer, nullable=True)
    created_utc = Column(DateTime, nullable=False)

    thread = relationship("Thread", back_populates="comments")
