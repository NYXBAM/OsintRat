from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def referral_button():
    rb = InlineKeyboardMarkup().add(
    InlineKeyboardButton("🎁 Get Free Searches", callback_data="show_referrals")
    )
    return rb
