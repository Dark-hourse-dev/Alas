"""
ALAS User Profile (L3) — SQLite-backed persistent user model.

Stores identity, communication preferences, emotional baselines,
and interaction patterns. Updated incrementally after each session.
"""

import json
from datetime import datetime, timezone as dt_timezone
from typing import Optional

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Float, create_engine, event
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.config import get_settings

Base = declarative_base()


class UserProfile(Base):
    """User profile database model."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, default="default")
    name = Column(String(256), nullable=True)
    preferred_name = Column(String(256), nullable=True)
    communication_style = Column(String(64), default="balanced")  # concise, detailed, balanced
    preferred_mode = Column(String(32), default="casual")  # work, casual, creative, learning
    topics_of_interest = Column(Text, default="[]")  # JSON array
    emotional_baseline = Column(String(32), default="neutral")
    interaction_count = Column(Integer, default=0)
    avg_session_length_mins = Column(Float, default=0.0)
    timezone = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(dt_timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(dt_timezone.utc),
                       onupdate=lambda: datetime.now(dt_timezone.utc))
    extra_data = Column(Text, default="{}")  # JSON blob for extensibility


class InteractionLog(Base):
    """Tracks high-level session metadata for behavioral analysis."""
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, default="default")
    session_id = Column(String(64), nullable=False)
    mode = Column(String(32), default="casual")
    message_count = Column(Integer, default=0)
    start_time = Column(DateTime, default=lambda: datetime.now(dt_timezone.utc))
    end_time = Column(DateTime, nullable=True)
    dominant_emotion = Column(String(32), nullable=True)
    topics = Column(Text, default="[]")  # JSON array
    satisfaction_score = Column(Float, nullable=True)  # -1 to 1


class ProfileStore:
    """
    Layer 3 — User Profile Store.
    
    Manages persistent user identity, preferences, and behavioral
    patterns using SQLite with SQLAlchemy ORM.
    """

    def __init__(self):
        settings = get_settings()
        db_url = f"sqlite:///{settings.sqlite_db_path}"
        self._engine = create_engine(db_url, echo=False)

        # Enable WAL mode for better concurrent reads
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self._engine)
        self._SessionLocal = sessionmaker(bind=self._engine)

    def _get_session(self) -> Session:
        return self._SessionLocal()

    def get_profile(self, user_id: str = "default") -> dict:
        """
        Get user profile as a dictionary.
        Creates a default profile if none exists.
        """
        with self._get_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)
                session.commit()
                session.refresh(profile)

            return {
                "user_id": profile.user_id,
                "name": profile.name,
                "preferred_name": profile.preferred_name,
                "communication_style": profile.communication_style,
                "preferred_mode": profile.preferred_mode,
                "topics_of_interest": json.loads(profile.topics_of_interest or "[]"),
                "emotional_baseline": profile.emotional_baseline,
                "interaction_count": profile.interaction_count,
                "avg_session_length_mins": profile.avg_session_length_mins,
                "timezone": profile.timezone,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
                "extra_data": json.loads(profile.extra_data or "{}"),
            }

    def update_profile(self, user_id: str = "default", **kwargs) -> dict:
        """
        Update user profile fields.
        
        Supports: name, preferred_name, communication_style, preferred_mode,
        topics_of_interest, emotional_baseline, timezone, extra_data
        """
        with self._get_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)

            for key, value in kwargs.items():
                if key == "topics_of_interest" and isinstance(value, list):
                    setattr(profile, key, json.dumps(value))
                elif key == "extra_data" and isinstance(value, dict):
                    existing = json.loads(profile.extra_data or "{}")
                    existing.update(value)
                    profile.extra_data = json.dumps(existing)
                elif hasattr(profile, key):
                    setattr(profile, key, value)

            profile.updated_at = datetime.now(dt_timezone.utc)
            session.commit()
            return self.get_profile(user_id)

    def increment_interaction(self, user_id: str = "default"):
        """Increment the interaction counter."""
        with self._get_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if profile:
                profile.interaction_count += 1
                profile.updated_at = datetime.now(dt_timezone.utc)
                session.commit()

    def log_session(
        self,
        session_id: str,
        mode: str = "casual",
        message_count: int = 0,
        dominant_emotion: Optional[str] = None,
        topics: Optional[list[str]] = None,
        user_id: str = "default",
    ):
        """Log session metadata for behavioral analysis."""
        with self._get_session() as session:
            log = InteractionLog(
                user_id=user_id,
                session_id=session_id,
                mode=mode,
                message_count=message_count,
                dominant_emotion=dominant_emotion,
                topics=json.dumps(topics or []),
            )
            session.add(log)
            session.commit()

    def get_interaction_history(self, user_id: str = "default", limit: int = 50) -> list[dict]:
        """Get recent interaction session logs."""
        with self._get_session() as session:
            logs = (
                session.query(InteractionLog)
                .filter_by(user_id=user_id)
                .order_by(InteractionLog.start_time.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "session_id": log.session_id,
                    "mode": log.mode,
                    "message_count": log.message_count,
                    "start_time": log.start_time.isoformat() if log.start_time else None,
                    "dominant_emotion": log.dominant_emotion,
                    "topics": json.loads(log.topics or "[]"),
                }
                for log in logs
            ]

# Singleton
_profile_store = None

def get_profile_store() -> ProfileStore:
    global _profile_store
    if _profile_store is None:
        _profile_store = ProfileStore()
    return _profile_store
