"""
Simple user command and message handlers 
TODO buttons 
"""

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from database import db
from utils.search_stub import deep_search, get_total_count, search_database, generate_results_file, is_database_online, detect_search_type
import config
import logging

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message):
    """
    Handle /start command.
    """
    user = db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    channel_link = f'<a href="https://t.me/{config.CHANNEL_USERNAME}"><b> UPDATE CHANNEL 🗞</b></a>'
    
    welcome_text = (
            f"👋 <b>Welcome to the OsintRat 🐀</b>\n\n"
            f"You can search for people by:\n"
            f"• Last name\n"
            f"• Email address\n"
            f"• Phone number\n"
            f"• @username\n"
            f"• id1234567890\n\n"
            f"Just type your query and I'll search for you.\n"
            f"To search by username, type @username. For user ID, type id12345678.\n\n"
            f"📊 <b>Your remaining free searches:</b> {user.free_searches_remaining}\n\n"
            f"Total records in database: {get_total_count()} lines\n\n"
            f"⚠ <i>Disclaimer:</i> All information in this bot is <b>generated</b>. "
            f"Any resemblance to real persons or data is purely <b>coincidental</b>.\n\n"
            f"HELP: {config.ADMIN_USERNAME}\n\n"
            f"Check out our {channel_link}!"
        )
    await message.answer(welcome_text, parse_mode="HTML", disable_web_page_preview=True)
    
async def cmd_help(message: types.Message):
    """Handle /help command."""
    help_text = (
        f"ℹ️ *How to use this bot*\n\n"
        f"Simply send me a search query:\n"
        f"• `John Smith` - Search by name\n"
        f"• `john@example.com` - Search by email\n"
        f"• `1234567890` - Search by phone\n"
        f"• `@username` - Search by username\n"
        f"• `id1234567890` - Search by userid\n\n"
        f"I'll search the database and send you results as a text file.\n\n"
        f"*Available commands:*\n"
        f"/start - Welcome message\n"
        f"/balance - Check remaining searches\n"
        f"/help - This help message\n\n"
        f"Each user gets {config.FREE_SEARCHES_PER_USER} free searches."
    )
    
    await message.answer(help_text, parse_mode='Markdown')

async def cmd_balance(message: types.Message):
    """get balance"""
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ User not found. Please use /start first.")
        return
    
    balance_text = (
        f"📊 *Your Search Balance*\n\n"
        f"Remaining free searches: {user.free_searches_remaining}\n\n"
        f"Need more searches? Contact the administrator.\n\n{config.ADMIN_USERNAME}"
    )
    
    await message.answer(balance_text, parse_mode='Markdown')

async def handle_search_query(message: types.Message):
    user = db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    if user.is_blocked:
        await message.answer(f"❌ Your account has been blocked. Please contact the administrator: {config.ADMIN_USERNAME}.")
        return
    
    if user.free_searches_remaining <= 0:
        await message.answer(
            "⚠️ You've reached your free search limit.\n\n"
            "Please contact the administrator to get more searches.\n\n"
            f"Contact: {config.ADMIN_USERNAME}"
        )
        return
    
    query = message.text.strip()
    
    if len(query) < 3:
        await message.answer("❌ Your query is too short. Please provide a more specific query.")
        return
    
    # Check if database is online
    if not await is_database_online():
        # Add to queue
        db.update_user_searches(user.telegram_id, decrement=True)
        db.add_to_queue(user.telegram_id, query)
        
        await message.answer(
            "⏸️ The database is currently offline.\n\n"
            "Your query has been added to the queue and will be processed "
            "automatically when the database comes back online.\n\n"
            "You'll receive a notification when your results are ready."
        )
        return
    
    # Send "searching" message
    search_msg = await message.answer("🔍 Searching in database...")
    
    try:
        # Detect search type
        search_type = detect_search_type(query)
        
        # Perform search (placeholder function)
        # results = await search_database(query, search_type)
        # TESTING DEEP SEARCH FOR ALL USERS 
        results = await deep_search(query, search_type)

        # Decrement user's search count
        db.update_user_searches(user.telegram_id, decrement=True)
        
        # Log the search
        db.log_search(
            user.telegram_id,
            query,
            search_type,
            results['results_found']
        )
        
        user = db.get_user(user.telegram_id)  # Refresh user data
        
        if results['results_found']:
            # Generate results file
            results_file = generate_results_file(results)
            
            await search_msg.edit_text(
                f"✅ Search complete!\n\n"
                f"Found {results['count']} result(s) for: {query}\n"
                f"Search type: {search_type}\n\n"
                f"📊 Remaining searches: {user.free_searches_remaining}"
            )
            
            # Send results file
            await message.answer_document(
                results_file,
                caption="Here are your search results.\n\n@OsintRatBot"
            )
        else:
            await search_msg.edit_text(
                f"❌ No results found for: {query}\n\n"
                f"Search type: {search_type}\n"
                f"📊 Remaining searches: {user.free_searches_remaining}"
            )
    
    except Exception as e:
        logging.error(f"Error processing search {e}")
        await search_msg.edit_text(
            "❌ An error occurred while processing your search. Please try again."
        )
        
        # Log failed search
        db.log_search(
            user.telegram_id,
            query,
            None,
            False,
            success=False
        )


def register_user_handlers(dp: Dispatcher):
    """
    Register all user handlers with the dispatcher.
    """
    # Command handlers
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_help, commands=['help'])
    dp.register_message_handler(cmd_balance, commands=['balance'])
    
    dp.register_message_handler(handle_search_query, content_types=['text'])