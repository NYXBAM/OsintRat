"""
Simple user command and message handlers 
TODO buttons 
"""

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot_instance import bot
from database import db
from utils.helper import decode_ref_id, encode_ref_id
from utils.keyboards.inline import referral_button
from utils.search_stub import deep_search, get_total_count, search_database, generate_results_file, is_database_online, detect_search_type
import config
import logging

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message):
    """
    Handle /start command.
    """
    bot_info = await bot.get_me()
    # bot_username = bot_info.username
    # ref_code = encode_ref_id(message.from_user.id)
    args = message.get_args()
    referrer_id = None
    if args:
        try:
            referrer_id = decode_ref_id(args)
        except Exception as e:
            logger.warning(f"Failed to decode referral code '{args}': {e}")
            referrer_id = None
    user, is_new = db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        referrer_id=referrer_id,
        return_tuple=True
    )
    
    if is_new:
        if referrer_id and referrer_id != message.from_user.id:
            try:
                new_user_name = (
                    f"@{message.from_user.username}"
                    if message.from_user.username
                    else message.from_user.first_name or str(message.from_user.id)
                )
                await bot.send_message(
                    referrer_id,
                    f"🎉 <b>You’ve got a new referral</b> — {new_user_name}!\n"
                    f"👏 You’ve earned + <b>{config.FREE_SEARCH_PER_REF} extra searches.</b>\n\n"
                    f"Thanks for helping grow us 🚀",
                    parse_mode='HTML'
                )

            except Exception as e:
                logger.warning(f"Error sending message to {referrer_id}: {e}")
                
    channel_link = f'<a href="https://t.me/{config.CHANNEL_USERNAME}"><b>UPDATE CHANNEL</b></a>'
    # welcome_text = (
    #         f"👋 <b>Welcome to the OsintRat 🐀</b>\n\n"
    #         f"You can search for people by:\n"
    #         f"• Last name\n"
    #         f"• Email address\n"
    #         f"• Phone number\n"
    #         f"• @username\n"
    #         f"• id1234567890\n\n"
    #         f"Just type your query and I'll search for you.\n"
    #         f"To search by username, type @username. For user ID, type id12345678.\n\n"
    #         f"📊 <b>Your remaining free searches:</b> {user.free_searches_remaining}\n\n"
    #         f"Total records in database: {get_total_count()} lines\n\n"
    #         f"⚠ <i>Disclaimer:</i> All information in this bot is <b>generated</b>. "
    #         f"<i>Any resemblance to real persons or data is purely <b>coincidental</b>.</i>\n\n"
    #         f"<i>This bot takes no responsibility for user-generated content. Any resemblance or</i>\n" 
    #         f"<i>coincidence is purely accidental. It was built for entertainment purposes only</i>\n" 
    #         f"<i>All information is either AI-generated or sourced from publicly available data.</i>\n"
    #         f"Check out our {channel_link}!\n\n\n"
    #         )
    
    welcome_text = (
            f"&#x1F44B; <b>Welcome to the OsintRatBot 🐀</b>\n\n"
            f"Your personal tool for quick and easy searches!\n"
            f"Simply type your query, and let the RAT do the work!\n\n"
            f"&#x1F50E; <b>Search by the following:</b>\n"
            f"&#x2022; Last Name\n"
            f"&#x2022; Email Address\n"
            f"&#x2022; Phone Number (e.g., <code>+780991234567</code>)\n"
            f"&#x2022; @ Username (e.g., <b>@ username</b>)\n"
            f"&#x2022; Telegram ID (e.g., <b>id1234567890</b>)\n\n"
            f"&#x1F4A1; <i>Remember:</i> To search by username, type <code>@</code> before the name. For a user ID, type <code>id</code> before the number.\n\n"
            f"----------------------------------\n"
            f"&#x1F4CA; <b>Your Search Stats</b>\n"
            f"<b>Remaining Free Searches:</b> <u>{user.free_searches_remaining}</u>\n"
            f"Total Records in Database: <i>{get_total_count()}</i> lines\n"
            f"----------------------------------\n\n"
            f"&#x26A0;&#xFE0F; <b>Important Disclaimer:</b>\n"
            f"All information in this bot is <b>AI-GENERATED</b> or sourced from publicly available data. "
            f"Any resemblance to real persons or data is purely <b>COINCIDENTAL</b> and accidental.\n\n"
            f"This bot was built for <i><b>entertainment purposes only</b></i> and takes no responsibility for user-generated content or coincidences.\n"
            f"Stay updated! \n\nCheck out our 📣  {channel_link}!\n\n\n"
            )
    await message.answer(welcome_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=referral_button())
    
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
        
async def show_referrals_callback(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    ref_code = encode_ref_id(callback.from_user.id)
    referral_link = f"https://t.me/{bot_username}?start={ref_code}"

    text = (
        f"🎁 <b>Your Referral Info</b>\n\n"
        f"👤 Referrals invited: <b>{user.referrals_count}</b>\n"
        f"🔍 Bonus searches earned: <b>{user.referrals_count * config.FREE_SEARCH_PER_REF}</b>\n\n"
        f"📎 <b>Your referral link:</b>\n{referral_link}\n\n"
        f"Invite friends and earn more free searches! 🚀"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")
        )
    )

    await callback.answer() 

async def back_to_main_callback(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_code = encode_ref_id(callback.from_user.id)
    channel_link = f'<a href="https://t.me/{config.CHANNEL_USERNAME}"><b> UPDATE CHANNEL</b></a>'

    welcome_text = (
            f"&#x1F44B; <b>Welcome to the OsintRatBot 🐀</b>\n\n"
            f"Your personal tool for quick and easy searches!\n"
            f"Simply type your query, and let the RAT do the work!\n\n"
            f"&#x1F50E; <b>Search by the following:</b>\n"
            f"&#x2022; Last Name\n"
            f"&#x2022; Email Address\n"
            f"&#x2022; Phone Number (e.g., <code>+780991234567</code>)\n"
            f"&#x2022; @ Username (e.g., <b>@ username</b>)\n"
            f"&#x2022; Telegram ID (e.g., <b>id1234567890</b>)\n\n"
            f"&#x1F4A1; <i>Remember:</i> To search by username, type <code>@</code> before the name. For a user ID, type <code>id</code> before the number.\n\n"
            f"----------------------------------\n"
            f"&#x1F4CA; <b>Your Search Stats</b>\n"
            f"<b>Remaining Free Searches:</b> <u>{user.free_searches_remaining}</u>\n"
            f"Total Records in Database: <i>{get_total_count()}</i> lines\n"
            f"----------------------------------\n\n"
            f"&#x26A0;&#xFE0F; <b>Important Disclaimer:</b>\n"
            f"All information in this bot is <b>AI-GENERATED</b> or sourced from publicly available data. "
            f"Any resemblance to real persons or data is purely <b>COINCIDENTAL</b> and accidental.\n\n"
            f"This bot was built for <i><b>entertainment purposes only</b></i> and takes no responsibility for user-generated content or coincidences.\n"
            f"Stay updated! \n\nCheck out our 📣 {channel_link}!\n\n\n"
            )

    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=referral_button()
    )

    await callback.answer()

def register_user_handlers(dp: Dispatcher):
    """
    Register all user handlers with the dispatcher.
    """
    # Command handlers
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_help, commands=['help'])
    dp.register_message_handler(cmd_balance, commands=['balance'])
    dp.register_callback_query_handler(show_referrals_callback, lambda c: c.data == "show_referrals")
    dp.register_callback_query_handler(back_to_main_callback, lambda c: c.data == "back_to_main")
    dp.register_message_handler(handle_search_query, content_types=['text'])