from aiogram import Bot

from tgbot.config import Config


async def notify_admin(bot: Bot, config: Config):
    admin_ids = config.tg_bot.admin_ids
    bot_name = config.tg_bot.bot_name
    for admin in admin_ids:
        await bot.send_message(chat_id=admin, text=f'Бот "{bot_name}" успешно запущен')
