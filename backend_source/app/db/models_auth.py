# backend_source/app/db/models_auth.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
import os

# Reuse engine, SessionLocal and Base from existing db.models if present.
# If not, fallback to creating a new Base (but project already has db/models.py).
try:
    # prefer importing existing SQLAlchemy objects to avoid multiple engines
    from app.db.models import engine, SessionLocal, Base  # existing file created earlier
except Exception:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vidreacher.db")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

class SocialAccount(Base):
    __tablename__ = "social_accounts"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), index=True)       # instagram, youtube, facebook
    account_id = Column(String(128), index=True)    # IG business id / YT channel ID / FB page ID
    access_token = Column(Text)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    meta_data = Column(JSON, nullable=True)         # store raw provider info
    created_at = Column(DateTime, default=datetime.utcnow)

class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), index=True)
    account_id = Column(String(128), index=True)
    followers = Column(Integer, nullable=True)
    views = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    impressions = Column(Integer, nullable=True)
    reach = Column(Integer, nullable=True)
    watch_time = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_auth_db():
    Base.metadata.create_all(bind=engine)