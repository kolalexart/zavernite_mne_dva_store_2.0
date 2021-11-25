import datetime
import typing

from aiogram.types import CallbackQuery, Message

from tgbot.db_api.postgres_db import delete_all_items_from_basket
from tgbot.misc.secondary_functions import get_scheduler, get_config


def clear_basket_on_schedule(obj: typing.Union[Message, CallbackQuery], added_at: datetime.datetime):
    config = get_config(obj)
    dsn = config.db.url
    scheduler = get_scheduler(obj)
    func = delete_all_items_from_basket
    kwargs = dict(dsn=dsn, telegram_id=obj.from_user.id)
    delete_time = added_at + datetime.timedelta(hours=3) + datetime.timedelta(seconds=30)
    job_id = f'clear_basket_{obj.from_user.id}'
    scheduler.add_job(func,
                      kwargs=kwargs,
                      trigger='date',
                      run_date=delete_time,
                      id=job_id,
                      replace_existing=True,
                      misfire_grace_time=None)
    return True


def remove_clear_basket_job(obj: typing.Union[Message, CallbackQuery], user_id: typing.Optional[int] = None):
    scheduler = get_scheduler(obj)
    job_id = f'clear_basket_{obj.from_user.id}'
    if user_id:
        job_id = f'clear_basket_{user_id}'
    scheduler.remove_job(job_id=job_id)
