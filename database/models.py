"""
Database models using SQLAlchemy ORM.
Defines the structure of tables for users, search logs, and query queue.
"""


from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    """
    Represents a Telegram user in the database.
    Tracks their search quota and account status.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    free_searches_remaining = Column(Integer, default=50)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    last_activity = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    referrer_id = Column(Integer, nullable=True)
    referrals_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class SearchLog(Base):
    """
    Logs all search queries made by users.
    Useful for analytics and debugging.
    """
    __tablename__ = 'search_logs'

    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(Integer, nullable=False, index=True)
    query = Column(Text, nullable=False)
    search_type = Column(String(50), nullable=True)  # e.g., 'name', 'email', 'phone'
    results_found = Column(Boolean, default=False)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),  
        nullable=False
    )
    success = Column(Boolean, default=True)

    def __repr__(self):
        return f"<SearchLog(user={self.user_telegram_id}, query={self.query[:20]})>"


class QueuedQuery(Base):
    """
    Stores queries that couldn't be processed due to database unavailability.
    These are processed when the database comes back online.
    """
    __tablename__ = 'queued_queries'

    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(Integer, nullable=False, index=True)
    query = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<QueuedQuery(user={self.user_telegram_id}, query={self.query[:20]})>"


class AdminLog(Base):
    """
    Logs all admin actions for future
    """
    __tablename__ = 'admin_logs'

    id = Column(Integer, primary_key=True)
    admin_telegram_id = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)  # e.g., 'block_user', 'add_requests'
    target_user_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AdminLog(admin={self.admin_telegram_id}, action={self.action})>"