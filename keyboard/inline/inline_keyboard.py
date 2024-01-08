from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

social_keyboard = InlineKeyboardBuilder()
social_keyboard.row(types.InlineKeyboardButton(
    text="Instagram", url="https://www.instagram.com/zorskidka?igshid=OGQ5ZDc2ODk2ZA==")
)
social_keyboard.row(types.InlineKeyboardButton(
    text="Telegram канал",
    url="https://t.me/ZorSkidka")
)
social_keyboard.row(types.InlineKeyboardButton(
    text="Подтвердить ✅",
    callback_data="verify")
)


def get_keyboard():
    buttons = [
        [
            types.InlineKeyboardButton(text="Да", callback_data="yes"),
            types.InlineKeyboardButton(text="Нет", callback_data="no")
        ],
    ]
    examination = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return examination


def send():
    button = [
        [
            types.InlineKeyboardButton(text="Да", callback_data="random_yes"),
            types.InlineKeyboardButton(text="Нет", callback_data="random_no")
        ],
    ]
    send = types.InlineKeyboardMarkup(inline_keyboard=button)
    return send
