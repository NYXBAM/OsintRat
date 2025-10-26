"""
Database connection and session management.
"""

import asyncio
from aiogram import Bot
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, User, SearchLog, QueuedQuery, AdminLog
from datetime import datetime, timezone
import config


engine = create_engine(config.DATABASE_URL, echo=False)


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
logger = logging.getLogger(__name__)


def init_db():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if not tables:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
    else:
        logger.info("ℹ️ Database already initialized")

def get_session() -> Session:
    """
    Get a new database session.
    """
    return SessionLocal()


# User management functions

def get_or_create_user(telegram_id: int, username: str = None, 
                       first_name: str = None, last_name: str = None,
                       referrer_id: int = None, return_tuple: bool = False) -> User:
    """
    Get an existing user or create a new one.
    New users start with the default number of free searches.
    """
    is_new = False
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if user:
            # Update user info and last activity
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.last_activity = datetime.now(timezone.utc)
        else:
            is_new = True
            # Create new user with free searches
            logger.info(f"New user: {telegram_id} ({username})")
            
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                free_searches_remaining=config.FREE_SEARCHES_PER_USER,
                referrer_id=referrer_id if referrer_id != telegram_id else None
            )
            session.add(user)
            
            if referrer_id and referrer_id != telegram_id:
                ref_user = session.query(User).filter(User.telegram_id == referrer_id).first()
                if ref_user:
                    ref_user.referrals_count = (ref_user.referrals_count or 0) + 1
                    ref_user.free_searches_remaining += config.FREE_SEARCH_PER_REF  
                    logger.info(f"Referral: {ref_user.telegram_id} -> {telegram_id}")
        
        
        session.commit()
        session.refresh(user)
        return (user, is_new) if return_tuple else user
    finally:
        session.close()


def get_user(telegram_id: int) -> User:
    """Get user by Telegram ID."""
    session = get_session()
    try:
        return session.query(User).filter(User.telegram_id == telegram_id).first()
    finally:
        session.close()


def update_user_searches(telegram_id: int, decrement: bool = True) -> bool:
    """
    Update user's remaining searches count.
    Returns True if successful, False if user has no searches left.
    """
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        if decrement:
            if user.free_searches_remaining > 0:
                user.free_searches_remaining -= 1
                session.commit()
                return True
            return False
        
        return True
    finally:
        session.close()


def add_user_searches(telegram_id: int, amount: int) -> bool:
    """Add free searches to a user's account."""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        user.free_searches_remaining += amount
        session.commit()
        return True
    finally:
        session.close()


def block_user(telegram_id: int, blocked: bool = True) -> bool:
    """Block or unblock a user."""
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        user.is_blocked = blocked
        session.commit()
        return True
    finally:
        session.close()


def get_all_users():
    """Get all users from the database."""
    session = get_session()
    try:
        return session.query(User).all()
    finally:
        session.close()


# Search log functions

def log_search(telegram_id: int, query: str, search_type: str = None, 
               results_found: bool = False, success: bool = True):
    """Log a search query to the database."""
    session = get_session()
    try:
        log_entry = SearchLog(
            user_telegram_id=telegram_id,
            query=query,
            search_type=search_type,
            results_found=results_found,
            success=success
        )
        session.add(log_entry)
        session.commit()
    finally:
        session.close()


# Queue management functions

def add_to_queue(telegram_id: int, query: str):
    """Add a query to the processing queue."""
    session = get_session()
    try:
        queued_query = QueuedQuery(
            user_telegram_id=telegram_id,
            query=query
        )
        session.add(queued_query)
        session.commit()
    finally:
        session.close()


def get_pending_queries():
    """Get all unprocessed queries from the queue."""
    session = get_session()
    try:
        return session.query(QueuedQuery).filter(QueuedQuery.processed == False).all()
    finally:
        session.close()


def mark_query_processed(query_id: int):
    """Mark a queued query as processed."""
    session = get_session()
    try:
        query = session.query(QueuedQuery).filter(QueuedQuery.id == query_id).first()
        if query:
            query.processed = True
            query.processed_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


# Admin log functions

def log_admin_action(admin_telegram_id: int, action: str, 
                    target_user_id: int = None, details: str = None):
    """Log an admin action to the database."""
    session = get_session()
    try:
        log_entry = AdminLog(
            admin_telegram_id=admin_telegram_id,
            action=action,
            target_user_id=target_user_id,
            details=details
        )
        session.add(log_entry)
        session.commit()
    finally:
        session.close()
        
    
async def send_all(bot: Bot, text: str):
    """Sending message to all users in the database (bot)"""
    session = get_session()
    try:
        users = session.query(User).filter_by(is_blocked=False).all()
        sent_count = 0
        failed_count = 0

        for user in users:
            try:
                await bot.send_message(chat_id=user.telegram_id, text=text, parse_mode='HTML')
                sent_count += 1
            except Exception as e:
                failed_count += 1
                #  delay 
            await asyncio.sleep(0.15)

        return {"sent": sent_count, "failed": failed_count}

    finally:
        session.close()