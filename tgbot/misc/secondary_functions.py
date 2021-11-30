import datetime
import re
import sys
import typing
from dataclasses import dataclass
from logging import Logger
from typing import Union, Optional

from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, InlineQuery, PreCheckoutQuery, Chat
from aiogram.utils.exceptions import MessageCantBeDeleted, MessageToDeleteNotFound
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asyncpg import Record

from tgbot.config import Config
from tgbot.db_api.postgres_db import Database
from tgbot.keyboards.inline import main_menu_keyboard
from tgbot.keyboards.menu_keyboards.admins_keybords.admins_menu import admins_menu_markup
from tgbot.misc.states import AdminActions


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


async def delete_message(target: typing.Union[Message, CallbackQuery], logger: Logger, reboot_photo: str,
                         reboot_text: str, state: Optional[FSMContext] = None):
    message = target if isinstance(target, Message) else target.message
    try:
        await message.delete()
    except (MessageCantBeDeleted, MessageToDeleteNotFound):
        await action_if_except(reboot_photo, reboot_text, state)
        return False
    except Exception as err:
        logger.exception('Message can\'t be deleted\n%s: %s', type(err), err)
        await action_if_except(reboot_photo, reboot_text, state)
        return False
    else:
        return True


async def bot_reboot(reboot_photo: str, reboot_text: str):
    markup = main_menu_keyboard()
    bot = Bot.get_current()
    chat = Chat.get_current()
    await bot.send_photo(chat_id=chat.id, photo=reboot_photo, caption=reboot_text,
                         reply_markup=markup)


async def action_if_except(reboot_photo: str, reboot_text: str, state: Optional[FSMContext] = None):
    if state:
        await state.finish()
    await bot_reboot(reboot_photo, reboot_text)


async def delete_message_for_admins(target: typing.Union[Message, CallbackQuery], logger: Logger,
                                    state: FSMContext):
    message = target if isinstance(target, Message) else target.message
    try:
        await message.delete()
    except (MessageCantBeDeleted, MessageToDeleteNotFound):
        await reboot_admins_menu(state)
        return False
    except Exception as err:
        logger.exception('Message can\'t be deleted\n%s: %s', type(err), err)
        await reboot_admins_menu(state)
        return False
    else:
        return True


async def reboot_admins_menu(state: FSMContext):
    await state.finish()
    markup = admins_menu_markup()
    text = 'Информация устарела. Администраторское меню перезапущено'
    bot = Bot.get_current()
    chat = Chat.get_current()
    await bot.send_message(chat_id=chat.id, text=text, reply_markup=markup)
    await AdminActions.add_or_change.set()


async def load_basket_payload(items_from_basket) -> typing.Optional[str]:
    if items_from_basket:
        payload = str()
        for item_from_basket in items_from_basket:
            item_in_basket: ItemInBasket = get_item_in_basket_data(item_from_basket)
            payload += f'{item_in_basket.item_id}:{item_in_basket.quantity}:'
        payload += 'b'
        return payload
    return


def check_payload(payload: typing.Optional[str]) -> bool:
    if not payload:
        return True

    else:
        return True if sys.getsizeof(payload) <= 118 else False


def check_price_list(items_from_basket: typing.Optional[list]) -> bool:
    if not items_from_basket:
        return True
    return True if len(items_from_basket) <= 9 else False
