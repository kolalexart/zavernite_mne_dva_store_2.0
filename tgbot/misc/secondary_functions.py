import datetime
import re
from dataclasses import dataclass
from typing import Union, Optional

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, InlineQuery, PreCheckoutQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asyncpg import Record

from tgbot.config import Config
from tgbot.db_api.postgres_db import Database


def get_db(obj: Union[Message, CallbackQuery, Dispatcher, InlineQuery, PreCheckoutQuery]) -> Database:
    return obj.bot.get("db")


def get_config(obj: Union[Message, CallbackQuery, Dispatcher]) -> Config:
    return obj.bot.get("config")


def get_scheduler(obj: Union[Message, CallbackQuery, Dispatcher]) -> AsyncIOScheduler:
    return obj.bot.get("scheduler")


class User:

    def __init__(self, telegram_id: int, username: Optional[str], full_name: str, email: Optional[str],
                 first_login_time: datetime.datetime):
        self.telegram_id = telegram_id
        self.username = username
        self.full_name = full_name
        self.email = email
        self.first_login_time = first_login_time


def get_user_data(user: Record) -> User:
    user_data = dict(user)
    telegram_id = user_data.get('telegram_id')
    username = user_data.get('username')
    full_name = user_data.get('full_name')
    email = user_data.get('email')
    first_login_time = user_data.get('first_login_time')
    return User(telegram_id, username, full_name, email, first_login_time)


@dataclass
class Item:
    item_id: int
    item_category_name: str
    item_category_code: int
    item_subcategory_name: str
    item_subcategory_code: int
    item_name: str
    item_photos: list
    item_price: int
    item_description: str
    item_short_description: str
    item_total_quantity: int
    item_discontinued: bool
    item_photo_url: str


def get_item_data(item: Record) -> Item:
    item_data = dict(item)
    item_id = item_data.get('item_id')
    item_category_name = item_data.get('item_category_name')
    item_category_code = item_data.get('item_category_code')
    item_subcategory_name = item_data.get('item_subcategory_name')
    item_subcategory_code = item_data.get('item_subcategory_code')
    item_name = item_data.get('item_name')
    item_photos = list(item_data.get('item_photos'))
    item_price = item_data.get('item_price')
    item_description = item_data.get('item_description')
    item_short_description = item_data.get('item_short_description')
    item_total_quantity = item_data.get('item_total_quantity')
    item_discontinued = item_data.get('item_discontinued')
    item_photo_url = item_data.get('item_photo_url')
    return Item(item_id, item_category_name, item_category_code, item_subcategory_name, item_subcategory_code,
                item_name, item_photos, item_price, item_description, item_short_description, item_total_quantity,
                item_discontinued, item_photo_url)


class ItemPatterns:
    # целое число в интревале от 1 до 9999
    ITEM_ID = re.compile('^[1-9][0-9]{0,3}$')

    # любой символ в количестве до 30 шт
    ITEM_CATEGORY_NAME = re.compile('^.{1,30}$')

    ITEM_SUBCATEGORY_NAME = re.compile('^.{1,30}$')

    ITEM_NAME = re.compile('^.{1,30}$')

    # целое число в интервале от 10 до 1000000
    ITEM_PRICE = re.compile('^[1-9][0-9][0-9]{0,4}$|^1000000$')

    # любой символ в количестве до 800 шт
    ITEM_DESCRIPTION = re.compile('^.{1,800}$')

    # любой символ в количестве до 32 шт
    ITEM_SHORT_DESCRIPTION = re.compile('^.{1,50}$')

    # целое число в интревале от 1 до 9999
    ITEM_TOTAL_QUANTITY = re.compile('^[1-9][0-9]{0,3}$|^0$')

    # сылка на jpeg
    ITEM_PHOTO_URL = re.compile('^https?://\S+\.(?:jpg|jpeg)$')


@dataclass
class ItemInBasket:
    full_name: str
    item_id: int
    item_name: str
    quantity: int
    item_price: int
    added_at: datetime.datetime


def get_item_in_basket_data(item_in_basket: Record) -> ItemInBasket:
    item_in_basket_data = dict(item_in_basket)
    full_name = item_in_basket_data.get('full_name')
    item_id = item_in_basket_data.get('item_id')
    item_name = item_in_basket_data.get('item_name')
    quantity = item_in_basket_data.get('quantity')
    item_price = item_in_basket_data.get('item_price')
    added_at = item_in_basket_data.get('added_at')
    return ItemInBasket(full_name, item_id, item_name, quantity, item_price, added_at)
