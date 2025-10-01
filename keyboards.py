from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Записаться")],
        [KeyboardButton(text="Мои заявки")],
        [KeyboardButton(text="О массаже")],
    ],
    resize_keyboard=True
)


def time_window_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Утро (08-10)", callback_data="tw:morning")],
        [InlineKeyboardButton(text="До обеда (10-12)", callback_data="tw:pre_lunch")],
        [InlineKeyboardButton(text="После обеда (12-16)", callback_data="tw:post_lunch")],
        [InlineKeyboardButton(text="Вечер до 18 (16-18)", callback_data="tw:eve_to_18")],
        [InlineKeyboardButton(text="С 18 до 20", callback_data="tw:18_20")],
    ])
    return kb


def intensity_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Расслабляющий", callback_data="int:relax")],
        [InlineKeyboardButton(text="Сбалансированный", callback_data="int:balanced")],
        [InlineKeyboardButton(text="Сильный", callback_data="int:strong")],
    ])
    return kb
