from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from database import db
from utils.search_stub import is_database_online
from utils.queue_manager import QueueManager
import config
from bot_instance import bot


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def cmd_admin(message: types.Message):
    """
    /admin command.
    Show admin panel with available commands.
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ You don't have admin permissions.")
        return
    
    admin_text = (
        "<b>🛠 Admin Panel</b>\n\n"
        "Available commands:\n\n"
        "<b>User Management:</b>\n"
        "/users - View all users\n"
        "/user &lt;telegram_id&gt; - View specific user info\n"
        "/add_requests &lt;telegram_id&gt; &lt;amount&gt; - Add free searches\n"
        "/block &lt;telegram_id&gt; - Block a user\n"
        "/unblock &lt;telegram_id&gt; - Unblock a user\n\n"
        "<b>System Management:</b>\n"
        "/queue - View pending queue\n"
        "/process_queue - Process queue manually\n"
        "/db_status - Check database status\n"
        "/db_online - Set database online (test)\n"
        "/db_offline - Set database offline (test)\n\n"
        "<b>Statistics:</b>\n"
        "/stats - View system statistics"
    )

    
    await message.answer(admin_text, parse_mode='html')


async def cmd_users(message: types.Message):
    """/users command - list all users."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ You don't have admin permissions.")
        return
    
    users = db.get_all_users()
    
    if not users:
        await message.answer("📋 No users found in database.")
        return
    
    users_text = f"👥 *All Users ({len(users)})*\n\n"
    
    for user in users[:20]:  # Limit to first 20 users
        status = "🔴 Blocked" if user.is_blocked else "🟢 Active"
        users_text += (
            f"ID: `{user.telegram_id}`\n"
            f"Name: {user.first_name or 'N/A'} {user.last_name or ''}\n"
            f"Username: @{user.username or 'N/A'}\n"
            f"Searches: {user.free_searches_remaining}\n"
            f"Status: {status}\n"
            f"Joined: {user.created_at.strftime('%Y-%m-%d')}\n"
            f"{'-' * 30}\n"
        )
    
    if len(users) > 20:
        users_text += f"\n... and {len(users) - 20} more users"
    
    await message.answer(users_text, parse_mode='Markdown')
    
    # Log admin action
    db.log_admin_action(message.from_user.id, "view_users")


async def cmd_user(message: types.Message):
    """Handle /user command - view specific user info."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ You don't have admin permissions.")
        return
    
    # Parse arguments
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /user <telegram_id>")
        return
    
    try:
        telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ Invalid telegram_id. Must be a number.")
        return
    
    user = db.get_user(telegram_id)
    
    if not user:
        await message.answer(f"❌ User with ID {telegram_id} not found.")
        return
    
    status = "🔴 Blocked" if user.is_blocked else "🟢 Active"
    
    user_text = (
        f"👤 *User Information*\n\n"
        f"Telegram ID: `{user.telegram_id}`\n"
        f"Name: {user.first_name or 'N/A'} {user.last_name or ''}\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Free Searches: {user.free_searches_remaining}\n"
        f"Status: {status}\n"
        f"Joined: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"Last Activity: {user.last_activity.strftime('%Y-%m-%d %H:%M')}"
    )
    
    await message.answer(user_text, parse_mode='Markdown')
    
    # Log admin action
    db.log_admin_action(message.from_user.id, "view_user", telegram_id)


async def cmd_add_requests(message: types.Message):
    """Handle /add_requests command - add free searches to user."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ You don't have admin permissions.")
        return
    
    # Parse arguments
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Usage: /add_requests <telegram_id> <amount>")
        return
    
    try:
        telegram_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("❌ Invalid arguments. Both must be numbers.")
        return
    
    if amount <= 0:
        await message.answer("❌ Amount must be positive.")
        return
    
    # Check if user exists
    user = db.get_user(telegram_id)
    if not user:
        await message.answer(f"❌ User with ID {telegram_id} not found.")
        return
    
    # Add searches
    success = db.add_user_searches(telegram_id, amount)
    
    if success:
        user = db.get_user(telegram_id)  # Refresh user data
        await message.answer(
            f"✅ Added {amount} free searches to user {telegram_id}\n"
            f"New balance: {user.free_searches_remaining}"
        )
        
        # Log admin action
        db.log_admin_action(
            message.from_user.id, 
            "add_requests", 
            telegram_id,
            f"Added {amount} searches"
        )
        
        # Notify user
        try:
            await message.bot.send_message(
                telegram_id,
                f"🎉 You've received {amount} additional free searches!\n"
                f"Your new balance: {user.free_searches_remaining}"
            )
        except Exception:
            pass  # User can block the bot
    else:
        await message.answer("❌ Failed to add searches. Please try again.")


async def cmd_block(message: types.Message):
    """Handle /block command - block a user."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ You don't have admin permissions.")
        return
    
    # Parse arguments
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /block <telegram_id>")
        return
    
    try:
        telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ Invalid telegram_id. Must be a number.")
        return
    
    # Check if user exists
    user = db.get_user(telegram_id)
    if not user:
        await message.answer(f"❌ User with ID {telegram_id} not found.")
        return
    
    # Block user
    success = db.block_user(telegram_id, blocked=True)
    
    if success:
        await message.answer(f"✅ User {telegram_id} has been blocked.")
        
        # Log admin action
        db.log_admin_action(message.from_user.id, "block_user", telegram_id)
        
        # Notify user
        try:
            await message.bot.send_message(
                telegram_id,
                "⛔️ Your account has been blocked by an administrator.\n"
                "Please contact support if you believe this is an error."
            )
        except Exception:
            pass
    else:
        await message.answer("❌ Failed to block user. Please try again.")


async def cmd_unblock(message: types.Message):
    """Handle /unblock command - unblock a user."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ You don't have admin permissions.")
        return
    
    # Parse arguments
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /unblock <telegram_id>")
        return
    
    try:
        telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ Invalid telegram_id. Must be a number.")
        return
    
    # Check if user exists
    user = db.get_user(telegram_id)
    if not user:
        await message.answer(f"❌ User with ID {telegram_id} not found.")
        return
    
    # Unblock user
    success = db.block_user(telegram_id, blocked=False)
    
    if success:
        await message.answer(f"✅ User {telegram_id} has been unblocked.")
        
        # Log admin action
        db.log_admin_action(message.from_user.id, "unblock_user", telegram_id)
        
        # Notify user
        try:
            await message.bot.send_message(
                telegram_id,
                "✅ Your account has been unblocked!\n"
                "You can now use the bot again."
            )
        except Exception:
            pass
    else:
        await message.answer("❌ Failed to unblock user. Please try again.")


async def cmd_queue(message: types.Message):
    """Handle /queue command - view pending queue."""
    if not is_admin(message.from_user.id):
        return
    
    pending = db.get_pending_queries()
    
    if not pending:
        await message.answer("📋 Queue is empty. No pending queries.")
        return
    
    queue_text = f"📋 *Pending Queue ({len(pending)} queries)*\n\n"
    
    for query in pending[:10]:  # Show first 10
        queue_text += (
            f"ID: {query.id}\n"
            f"User: {query.user_telegram_id}\n"
            f"Query: {query.query[:50]}...\n"
            f"Created: {query.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"{'-' * 30}\n"
        )
    
    if len(pending) > 10:
        queue_text += f"\n... and {len(pending) - 10} more queries"
    
    await message.answer(queue_text)

async def cmd_db_status(message: types.Message):
    """Handle /db_status command - check database status."""
    if not is_admin(message.from_user.id):
        return
    
    status = "🟢 ONLINE" if await is_database_online() else "🔴 OFFLINE"
    pending = db.get_pending_queries()
    
    status_text = (
        f"🗄 *Database Status*\n\n"
        f"Status: {status}\n"
        f"Pending queries: {len(pending)}"
    )
    
    await message.answer(status_text, parse_mode='Markdown')


async def cmd_stats(message: types.Message):
    """Handle /stats command - view system statistics."""
    if not is_admin(message.from_user.id):
        return
    
    users = db.get_all_users()
    pending = db.get_pending_queries()
    
    total_users = len(users)
    active_users = sum(1 for u in users if not u.is_blocked)
    blocked_users = sum(1 for u in users if u.is_blocked)
    total_searches = sum(config.FREE_SEARCHES_PER_USER - u.free_searches_remaining for u in users)
    
    stats_text = (
        f"📊 *System Statistics*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🟢 Active: {active_users}\n"
        f"🔴 Blocked: {blocked_users}\n\n"
        f"🔍 Total Searches Performed: {total_searches}\n"
        f"📋 Pending Queue: {len(pending)}\n\n"
        f"🗄 Database: {'🟢 Online' if await is_database_online() else '🔴 Offline'}"
    )
    
    await message.answer(stats_text, parse_mode='Markdown')
    
    # Log admin action
    db.log_admin_action(message.from_user.id, "view_stats")

async def cmd_send_all(message: types.Message):
    """Handle /broadcast command - send message to all users."""
    if not is_admin(message.from_user.id):
        return

    text = message.get_args()
    if not text:
        return await message.reply("/broadcast <text>")

    await message.reply("🚀 Starting broadcasting...")
    stats = await db.send_all(bot, text)
    await message.reply(
        f"✅ Finished sending!\n"
        f"📬 Succesfully: {stats['sent']}\n"
        f"❌ Failed: {stats['failed']}"
    )



def register_admin_handlers(dp: Dispatcher):
    """
    Register all admin handlers with the dispatcher.
    """
    dp.register_message_handler(cmd_admin, commands=['admin'])
    dp.register_message_handler(cmd_users, commands=['users'])
    dp.register_message_handler(cmd_user, commands=['user'])
    dp.register_message_handler(cmd_add_requests, commands=['add_requests'])
    dp.register_message_handler(cmd_block, commands=['block'])
    dp.register_message_handler(cmd_unblock, commands=['unblock'])
    dp.register_message_handler(cmd_queue, commands=['queue'])
    dp.register_message_handler(cmd_db_status, commands=['db_status'])
    dp.register_message_handler(cmd_stats, commands=['stats'])
    dp.register_message_handler(cmd_send_all, commands=['send_all'])