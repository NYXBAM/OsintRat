"""
Queue manager for handling queries when database is offline.
Processes queued queries when database comes back online.
"""

import asyncio
from aiogram import Bot
from database import db
from utils.search_stub import deep_search, search_database, generate_results_file, is_database_online
import config
import logging

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Manages the query queue and processes pending queries.
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_processing = False
    
    async def process_queue(self):
        """
        Process all pending queries in the queue.
        This is called when the database comes back online.
        """
        
        if self.is_processing:
            return
        
        if not await is_database_online():
            return
        
        self.is_processing = True
        
        try:
            pending_queries = db.get_pending_queries()
            
            if not pending_queries:
                return
            
            for query in pending_queries:
                try:
                    # Get user info
                    user = db.get_user(query.user_telegram_id)
                    
                    if not user:
                        db.mark_query_processed(query.id)
                        continue
                    
                    # Check if user is blocked
                    if user.is_blocked:
                        await self.bot.send_message(
                            query.user_telegram_id,
                            "❌ Your account has been blocked. Cannot process your queued query."
                        )
                        db.mark_query_processed(query.id)
                        continue
                    
                    # Perform the search
                    # results = await search_database(query.query)
                    # trying deep search
                    results = await deep_search(query.query)
                    
                    # Log the search
                    db.log_search(
                        query.user_telegram_id,
                        query.query,
                        results['search_type'],
                        results['results_found']
                    )
                    
                    # Generate and send results file
                    results_file = generate_results_file(results)
                    
                    await self.bot.send_message(
                        query.user_telegram_id,
                        f"✅ Your queued query has been processed!\n\n"
                        f"Query: {query.query}\n"
                        f"Results found: {results['count']}"
                    )
                    
                    await self.bot.send_document(
                        query.user_telegram_id,
                        results_file,
                        caption="Here are your search results."
                    )
                    
                    # Mark as processed
                    db.mark_query_processed(query.id)
                    
                    # Small delay to avoid flooding
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing queued query {query.id}: {e}")
                    db.mark_query_processed(query.id)
                    # Continue with next query even if one fails
                    continue
            
            
        finally:
            self.is_processing = False
    
    async def start_periodic_check(self):
        """
        Start periodic checking of the queue.
        This runs in the background and processes queues when DB is online.
        """
        logger.info(f"Starting periodic queue check (every {config.QUEUE_CHECK_INTERVAL}s)")
        
        while True:
            try:
                await asyncio.sleep(config.QUEUE_CHECK_INTERVAL)
                
                if await is_database_online():
                    await self.process_queue()
                else:
                    pass
                    
            except Exception as e:
                logger.error(f"Error in periodic queue check: {e}")
                # Continue running even if there's an error
                continue