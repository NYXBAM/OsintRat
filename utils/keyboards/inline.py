from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def referral_button():
    rb = InlineKeyboardMarkup().add(
    InlineKeyboardButton("🎁 Get Free Searches", callback_data="show_referrals")
    )
    return rb

def advanced_search_button():
    button = InlineKeyboardMarkup().add(
    InlineKeyboardButton("Advanced search - 1 credit", callback_data="advanced_search")
    )
    return button