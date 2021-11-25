from aiogram import Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeDefault, BotCommandScopeChat

from tgbot.config import Config
from tgbot.misc.secondary_functions import get_config


async def set_bot_commands(dp: Dispatcher):

    # для администраторов
    config = get_config(dp)
    for telegram_id in config.tg_bot.admin_ids:
        await dp.bot.set_my_commands(commands=[
            BotCommand('start', 'Начать работу с ботом магазина "Заверните мне два"'),
            BotCommand('menu', 'Посмотри, что есть у нас в магазине'),
            BotCommand('get_link', 'Получить ссылку для привлечения рефералов'),
            BotCommand('help', 'Помощь по командам и функционалу'),
            BotCommand('admins_menu', 'Показать меню администраторов'),
            BotCommand('exit', 'ONLY FOR ADMINS Выйти из всех состояний'),
            BotCommand('get_photo_id', 'Получить ID фото')
        ], scope=BotCommandScopeChat(chat_id=telegram_id))

    # для личных чатов с ботом
    await dp.bot.set_my_commands(commands=[
        BotCommand('start', 'Начать работу с ботом магазина "Заверните мне два"'),
        BotCommand('menu', 'Посмотри, что есть у нас в магазине'),
        BotCommand('get_link', 'Получить ссылку для привлечения рефералов'),
        BotCommand('help', 'Помощь по командам и функционалу')
    ], scope=BotCommandScopeAllPrivateChats())
