"""
Configuration file
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot API Token
# Get it from @BotFather on Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")

# List of admin Telegram user IDs
# Users in this list have access to admin commands

_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in _admins.split(",") if x.strip()]

# Admin username
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# Channel url or username 
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
# Database configuration
DATABASE_URL = "sqlite:///bot_database.db"

# User quota settings
FREE_SEARCHES_PER_USER = 50
# Search per refferal 
FREE_SEARCH_PER_REF = 5
# Queue processing interval (in seconds)
QUEUE_CHECK_INTERVAL = 60  # Check every 60 seconds

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"

# Meilisearch configuration

CLIENT_URL=os.getenv("CLIENT_URL")

