import asyncio
import logging
import os

import pytz
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.redis import RedisJobStore
# from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tgbot.config import load_config
from tgbot.db_api.postgres_db import Database
from tgbot.filters.admin import AdminFilter
from tgbot.handlers.admins.admin_add_item import register_admin_add_item
from tgbot.handlers.admins.admin_change_item import register_admin_change_item
from tgbot.handlers.admins.admin_change_or_delete_item_category import register_admin_change_or_delete_item_category
from tgbot.handlers.admins.admin_main import register_admin_main
# from tgbot.handlers.echo import register_echo
from tgbot.handlers.error_handler import register_error
from tgbot.handlers.inline_mode import register_inline_mode
from tgbot.handlers.payments.telegram_built_in.telegram_payment import register_telegram_built_in_payments
from tgbot.handlers.user import register_user
from tgbot.middlewares.album import AlbumMiddleware
from tgbot.middlewares.telegraph import IntegrationMiddleware
from tgbot.middlewares.throttling import ThrottlingMiddleware
from tgbot.misc.allowed_updates import get_handled_updates_list
from tgbot.misc.on_startup import notify_admin
from tgbot.misc.set_bot_commands import set_bot_commands
from tgbot.services.integrations.telegraph.abstract import FileUploader
from tgbot.services.integrations.telegraph.service import TelegraphService

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')


def register_all_middlewares(dp):
    dp.setup_middleware(ThrottlingMiddleware())
    dp.setup_middleware(AlbumMiddleware())


async def close_session_file_uploader(dp: Dispatcher, cur_logger: logging.Logger):
    file_uploader: FileUploader = dp.bot.get('file_uploader')
    await file_uploader.close()
    cur_logger.info('FileUploader session has been closed')


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    register_inline_mode(dp)
    register_admin_main(dp)
    register_admin_add_item(dp)
    register_admin_change_item(dp)
    register_admin_change_or_delete_item_category(dp)
    register_user(dp)
    register_telegram_built_in_payments(dp)
    register_error(dp)
    # register_echo(dp)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',

    )
    logger.info("Starting bot")
    config = load_config(database_url=DATABASE_URL, path=".env")

    if config.tg_bot.use_redis:
        storage = RedisStorage2(host=config.redis.redis_host, port=config.redis.redis_port)
    else:
        storage = MemoryStorage()

    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dp = Dispatcher(bot, storage=storage)
    # jobstores = {
    #     'default': SQLAlchemyJobStore(url=config.db.url)
    # }
    jobstores = {
        'default': RedisJobStore(
            db=config.redis.redis_db_jobstore, host=config.redis.redis_host, port=config.redis.redis_port
        )
    }
    executors = {'default': AsyncIOExecutor()}
    job_defaults = {"coalesce": False, "max_instances": 3, "misfire_grace_time": None}
    scheduler = AsyncIOScheduler(jobstores=jobstores,
                                 executors=executors,
                                 job_defaults=job_defaults,
                                 timezone=pytz.timezone('Europe/Moscow'))

    db = Database(url=config.db.url)

    file_uploader = TelegraphService()

    bot['config'] = config
    bot['scheduler'] = scheduler
    bot['db'] = db
    bot['file_uploader'] = file_uploader

    dp.setup_middleware(IntegrationMiddleware(file_uploader))
    register_all_middlewares(dp)
    register_all_filters(dp)
    register_all_handlers(dp)

    # start
    try:
        await db.connect_to_database()
        logger.info('Database connection has been completed')
        await set_bot_commands(dp)
        logger.info('Bot commands have setted')
        # await db.drop_table('users')
        await db.create_table_users()
        logger.info('Table "users" have been created')
        # await db.drop_table('basket')
        # await db.drop_table('items')
        await db.create_table_items()
        # await db.del_all_items_from_table('items')
        logger.info('Table "items" have been created')
        await db.create_table_basket()
        logger.info('Table "basket" have been created')
        scheduler.start()
        await notify_admin(bot, config)
        await dp.start_polling(dp, allowed_updates=get_handled_updates_list(dp))
    finally:
        scheduler.shutdown()
        await db.pool.close()
        await close_session_file_uploader(dp, logger)
        await dp.storage.close()
        await dp.storage.wait_closed()
        await dp.bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
