from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

from tgbot.misc.links import StoreLinks

main_menu_cd = CallbackData('main_menu', 'button')


def main_menu_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.insert(InlineKeyboardButton(text='Каталог', callback_data=main_menu_cd.new(button='catalog')))
    markup.insert(InlineKeyboardButton(text='О нас', callback_data=main_menu_cd.new(button='about_us')))
    markup.insert(InlineKeyboardButton(text='Помощь', callback_data=main_menu_cd.new(button='help')))
    markup.insert(InlineKeyboardButton(text='Задать вопрос', url=StoreLinks.STORE_TELEGRAM_LINK))
    markup.insert(InlineKeyboardButton(text='Написать разработчику', url=StoreLinks.APPLICATION_DEVELOPER_LINK))
    if StoreLinks.STORE_SITE_LINK:
        markup.insert(InlineKeyboardButton(text='Перейти на сайт', url=StoreLinks.STORE_SITE_LINK))
    if StoreLinks.STORE_INSTAGRAM_LINK:
        markup.insert(InlineKeyboardButton(text='Мы в Instagram', url=StoreLinks.STORE_INSTAGRAM_LINK))
    if StoreLinks.LEGAL_INFORMATION_LINK:
        markup.row(InlineKeyboardButton(text='Юридическая информация',
                                        url=StoreLinks.LEGAL_INFORMATION_LINK))
    else:
        markup.row(InlineKeyboardButton(text='Юридическая информация',
                                        callback_data=main_menu_cd.new(button='legal_information')))
    return markup
