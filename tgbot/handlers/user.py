import datetime
import logging
import typing

from aiogram import Dispatcher, types, Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, Command, CommandHelp, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, MediaGroup, \
    InputMediaPhoto, PreCheckoutQuery
from aiogram.utils.deep_linking import get_start_link, decode_payload
from aiogram.utils.exceptions import MessageNotModified, BotBlocked
from apscheduler.jobstores.base import JobLookupError

from tgbot.keyboards.inline import main_menu_keyboard, main_menu_cd
from tgbot.keyboards.menu_keyboards.users_keyboards.menu_inline import categories_keyboard, subcategories_keyboard, \
    items_keyboard, item_keyboard, menu_cd, edit_quantity_cd, scroll_items_cd, more_photos_cd, \
    back_button_keyboard_for_more_photos, add_to_basket_cd, basket_cd, edit_basket_markup
from tgbot.misc.schedule import clear_basket_on_schedule, remove_clear_basket_job
from tgbot.misc.secondary_functions import get_db, get_user_data, get_item_data, Item, ItemInBasket, \
    get_item_in_basket_data, User, delete_message, load_basket_payload, check_payload, check_price_list
from tgbot.misc.texts import UserTexts

logger = logging.getLogger(__name__)


async def create_start_link(message: Message, state: FSMContext):
    await state.finish()
    deep_link = await get_start_link(payload=str(message.from_user.id), encode=True)
    await message.answer(f'Ваша ссылка для привлечения рефералов. Скопируй ее или просто '
                         f'перешли другу ⬇⬇⬇')
    await message.answer(deep_link)


async def get_referer(message: Message, decoded_args: typing.Optional[int]) -> typing.Union[User, None]:
    db = get_db(message)
    if decoded_args:
        referer_record = await db.select_item_from_table('users', telegram_id=decoded_args)
        if referer_record:
            referer = get_user_data(referer_record)
            return referer
    return


async def notify_referer(referer: typing.Optional[User], user: User):
    if referer:
        bot = Bot.get_current()
        try:
            text = f'{referer.full_name}, по вашей ссылке зарегистрировался пользователь {user.full_name}'
            await bot.send_message(chat_id=referer.telegram_id, text=text)
        except BotBlocked:
            pass
        except Exception as err:
            logger.exception('%s: %s', type(err), err)


async def select_or_add_user_from_or_to_database(message: Message, decoded_args: typing.Optional[int] = None) -> \
        typing.Tuple[User, bool, typing.Optional[User]]:
    referer = await get_referer(message, decoded_args)
    db = get_db(message)
    new_user = False
    user_record = await db.select_item_from_table('users', telegram_id=message.from_user.id)
    if not user_record:
        user_record = await db.add_new_user(telegram_id=message.from_user.id,
                                            username=message.from_user.username,
                                            full_name=message.from_user.full_name,
                                            email=None,
                                            first_login_time=datetime.datetime.utcnow(),
                                            referer_telegram_id=referer.telegram_id if referer else None)
        new_user = True
    user = get_user_data(user_record)
    await notify_referer(referer, user)
    return user, new_user, referer


def check_on_start_args(encoded_args: typing.Optional[str]):
    if encoded_args:
        try:
            decoded_args_str = decode_payload(encoded_args)
        except UnicodeDecodeError:
            return
        except Exception as err:
            logger.exception('%s: %s', type(err), err)
            return
        else:
            try:
                decoded_args = int(decoded_args_str)
            except Exception as err:
                logger.exception('%s: %s', type(err), err)
                return
            else:
                return decoded_args
    return


async def user_start(message: Message, state: FSMContext):
    await state.finish()
    encoded_args = message.get_args()
    decoded_args = check_on_start_args(encoded_args)
    user, new_user, referer = await select_or_add_user_from_or_to_database(message, decoded_args)
    markup = main_menu_keyboard()
    caption = UserTexts.user_hello_new_user(user, referer) if new_user else UserTexts.user_hello_old_user(user)
    await message.answer_photo(photo=UserTexts.PHOTO_LOGO,
                               caption=caption,
                               reply_markup=markup)


async def user_help(obj: typing.Union[Message, CallbackQuery], state: FSMContext):
    if isinstance(obj, Message):
        await state.finish()
        message = obj
        await message.answer_photo(photo=UserTexts.PHOTO_LOGO, caption=UserTexts.USER_HELP),
    elif isinstance(obj, CallbackQuery):
        call = obj
        await call.answer(cache_time=1)
        callback_data = main_menu_cd.new(button='main_menu')
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='В главное меню',
                                                                             callback_data=callback_data)]])
        await call.message.edit_caption(caption=UserTexts.USER_HELP, reply_markup=markup)


async def about_us(call: CallbackQuery):
    await call.answer(cache_time=1)
    callback_data = main_menu_cd.new(button='main_menu')
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='В главное меню',
                                                                         callback_data=callback_data)]])
    await call.message.edit_caption(caption=UserTexts.USER_ABOUT_US, reply_markup=markup)


async def legal_information(call: CallbackQuery):
    await call.answer(cache_time=1)
    callback_data = main_menu_cd.new(button='main_menu')
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='В главное меню',
                                                                         callback_data=callback_data)]])
    await call.message.edit_caption(caption=UserTexts.USER_LEGAL_INFORMATION, reply_markup=markup)


async def back_to_main_menu(call: CallbackQuery):
    await call.answer(cache_time=1)
    markup = main_menu_keyboard()
    await call.message.edit_caption(caption=UserTexts.USER_BACK_TO_MAIN_MENU, reply_markup=markup)


async def show_store_menu(obj: typing.Union[Message, CallbackQuery], state: FSMContext):
    if isinstance(obj, Message):
        await state.finish()
    await list_categories(obj)


async def list_categories(obj: typing.Union[Message, CallbackQuery]):
    markup = await categories_keyboard(obj)
    text = UserTexts.USER_MENU
    if isinstance(obj, Message):
        message = obj
        await message.answer_photo(photo=UserTexts.PHOTO_LOGO, caption=text, reply_markup=markup)
    elif isinstance(obj, CallbackQuery):
        call = obj
        if call.message.content_type == types.ContentType.PHOTO:
            await call.answer(cache_time=1)
            await call.message.edit_caption(caption=text, reply_markup=markup)
        else:
            await call.answer(cache_time=1)
            # await call.message.delete()
            if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
                await call.message.answer_photo(photo=UserTexts.PHOTO_LOGO, caption=text, reply_markup=markup)


async def list_subcategories(call: CallbackQuery, item_category_code: int):
    markup = await subcategories_keyboard(call, item_category_code)
    if call.message.caption == UserTexts.USER_MENU:
        await call.message.edit_reply_markup(reply_markup=markup)
    else:
        await call.message.edit_caption(UserTexts.USER_MENU, reply_markup=markup)


async def list_items(call: CallbackQuery, item_category_code: int, item_subcategory_code: int):
    markup = await items_keyboard(call, item_category_code, item_subcategory_code)
    if call.message.caption == UserTexts.USER_MENU:
        await call.message.edit_reply_markup(markup)
    else:
        # await call.message.delete()
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(photo=UserTexts.PHOTO_LOGO, caption=UserTexts.USER_MENU,
                                            reply_markup=markup)


async def get_item(obj: typing.Union[Message, CallbackQuery, PreCheckoutQuery], item_id: int) -> \
        typing.Union[Item, None]:
    db = get_db(obj)
    item_record = await db.get_item_from_items(item_id)
    if item_record:
        item = get_item_data(item_record)
        return item
    return


def create_photo_media_group(photos: typing.List[str]) -> MediaGroup:
    media_group = MediaGroup()
    for photo in photos:
        input_media_photo = InputMediaPhoto(photo)
        media_group.attach_photo(input_media_photo)
    return media_group


async def show_item(call: CallbackQuery, item_id: int):
    item = await get_item(call, item_id)
    if item:
        markup = await item_keyboard(call, item, quantity=1)
        # await call.message.delete()
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(photo=item.item_photos[0], caption=UserTexts.item_text(item),
                                            reply_markup=markup)
    else:
        await call.message.edit_caption(UserTexts.user_products_out_of_stock_while_change(item_id),
                                        reply_markup=await categories_keyboard(call))


async def navigate(call: CallbackQuery, callback_data: dict):
    current_level = int(callback_data.get('level'))
    item_category_code = int(callback_data.get('item_category_code'))
    item_subcategory_code = int(callback_data.get('item_subcategory_code'))
    item_id = int(callback_data.get('item_id'))

    if current_level == 0:
        await list_categories(call)
    else:
        await call.answer(cache_time=1)
        if current_level == 1:
            await list_subcategories(call, item_category_code)
        elif current_level == 2:
            await list_items(call, item_category_code, item_subcategory_code)
        elif current_level == 3:
            await show_item(call, item_id)


async def get_data_for_edit_quantity(call: CallbackQuery, callback_data: dict) -> typing.Tuple[Item, int, int]:
    item_id = int(callback_data.get('item_id'))
    quantity = int(callback_data.get('quantity'))
    item = await get_item(call, item_id)
    return item, quantity, item_id


async def increase_quantity(call: CallbackQuery, callback_data: dict):
    item, quantity, item_id = await get_data_for_edit_quantity(call, callback_data)
    if item:
        if quantity < item.item_total_quantity:
            await call.answer(cache_time=1)
            quantity += 1
        try:
            markup = await item_keyboard(call, item, quantity)
            await call.message.edit_reply_markup(reply_markup=markup)
        except MessageNotModified:
            await call.answer(text=f'{quantity} - это максимальное количество данного товара на складе',
                              show_alert=True)
    else:
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO,
                                            UserTexts.user_products_out_of_stock_while_change(item_id),
                                            reply_markup=await categories_keyboard(call))


async def decrease_quantity(call: CallbackQuery, callback_data: dict):
    item, quantity, item_id = await get_data_for_edit_quantity(call, callback_data)
    if item:
        if quantity > 1:
            await call.answer(cache_time=1)
            quantity -= 1
        try:
            markup = await item_keyboard(call, item, quantity)
            await call.message.edit_reply_markup(reply_markup=markup)
        except MessageNotModified:
            await call.answer(text=f'{quantity} - это минимально возможное количество данного товара для покупки',
                              show_alert=True)
    else:
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO,
                                            UserTexts.user_products_out_of_stock_while_change(item_id),
                                            reply_markup=await categories_keyboard(call))


def get_data_for_scroll_items(callback_data: dict) -> typing.Tuple[int, int, int]:
    item_id = int(callback_data.get('item_id'))
    item_category_code = int(callback_data.get('item_category_code'))
    item_subcategory_code = int(callback_data.get('item_subcategory_code'))
    return item_id, item_category_code, item_subcategory_code


def determine_next_item_id(scroll_direction: str, current_item_id: int, list_items_ids: typing.List[int]):
    try:
        current_item_id_index = list_items_ids.index(current_item_id)
    except ValueError:
        return list_items_ids[0]
    else:
        if scroll_direction == 'right':
            next_item_id_index = current_item_id_index + 1 if current_item_id_index != len(list_items_ids) - 1 else 0
            next_item_id = list_items_ids[next_item_id_index]
            return next_item_id
        elif scroll_direction == 'left':
            next_item_id_index = current_item_id_index - 1 if current_item_id_index != 0 else len(list_items_ids) - 1
            next_item_id = list_items_ids[next_item_id_index]
            return next_item_id


async def determine_next_item(call: CallbackQuery, item_id: int, item_category_code: int, item_subcategory_code,
                              scroll_direction: str) -> typing.Union[Item, None]:
    db = get_db(call)
    items_records = await db.get_items_from_items(item_category_code, item_subcategory_code)
    list_items_ids = [item_record.get('item_id') for item_record in items_records]
    if list_items_ids:
        if len(list_items_ids) == 1 and list_items_ids[0] == item_id:
            await call.answer(text='В этой категории только один товар. Листать некуда', show_alert=True)
            return
        elif len(list_items_ids) == 1:
            await call.answer(cache_time=1)
            item = get_item_data(items_records[0])
            return item
        else:
            await call.answer(cache_time=1)
            next_item_id = determine_next_item_id(scroll_direction=scroll_direction, current_item_id=item_id,
                                                  list_items_ids=list_items_ids)
            item = [get_item_data(item_record) for item_record in items_records if
                    item_record.get('item_id') == next_item_id][0]
            return item
    else:
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO,
                                            UserTexts.user_products_out_of_stock_while_change(item_id),
                                            reply_markup=await categories_keyboard(call))
            return


async def scroll_items(call: CallbackQuery, callback_data: dict, scroll_direction: str):
    item = await determine_next_item(call, *get_data_for_scroll_items(callback_data), scroll_direction=scroll_direction)
    if item:
        markup = await item_keyboard(call, item, quantity=1)
        # await call.message.delete()
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(item.item_photos[0], caption=UserTexts.item_text(item), reply_markup=markup)
    else:
        return


async def scroll_items_right(call: CallbackQuery, callback_data: dict, scroll_direction='right'):
    await scroll_items(call, callback_data, scroll_direction)


async def scroll_items_left(call: CallbackQuery, callback_data: dict, scroll_direction='left'):
    await scroll_items(call, callback_data, scroll_direction)


async def get_data_for_more_photos(call: CallbackQuery, callback_data: dict) -> typing.Tuple[Item, int]:
    item_id = int(callback_data.get('item_id'))
    item = await get_item(call, item_id)
    return item, item_id


async def prepare_ids_messages_to_delete(call: CallbackQuery, media_group: MediaGroup) -> list:
    messages_to_delete = await call.message.answer_media_group(media_group)
    ids_list_messages_to_delete = [message_to_delete.message_id for message_to_delete in messages_to_delete]
    return ids_list_messages_to_delete


async def more_photos(call: CallbackQuery, callback_data: dict, state: FSMContext):
    item, item_id = await get_data_for_more_photos(call, callback_data)
    if item:
        markup = back_button_keyboard_for_more_photos(item_id)
        if len(item.item_photos) > 1:
            await call.answer(cache_time=1)
            if len(item.item_photos) == 2:
                # await call.message.delete()
                if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT, state):
                    await call.message.answer_photo(photo=item.item_photos[1], reply_markup=markup)
            else:
                if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT, state):
                    media_group = create_photo_media_group(item.item_photos[1:])
                    # await call.message.delete()
                    ids_list_messages_to_delete = await prepare_ids_messages_to_delete(call, media_group)
                    await state.update_data(messages_to_delete=ids_list_messages_to_delete)
                    await call.message.answer('Чтобы продолжить, нажмите "Назад"', reply_markup=markup)
        else:
            await call.answer('У этого товара только одно фото', show_alert=True)
    else:
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO,
                                            UserTexts.user_products_out_of_stock_while_change(item_id),
                                            reply_markup=await categories_keyboard(call))


async def back_to_main_photo(call: CallbackQuery, callback_data, state: FSMContext):
    item, item_id = await get_data_for_more_photos(call, callback_data)
    if item:
        markup = await item_keyboard(call, item, quantity=1)
        data_from_state = await state.get_data()
        ids_list_messages_to_delete = data_from_state.get('messages_to_delete')
        # await call.message.delete()
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT, state):
            if ids_list_messages_to_delete:
                for id_message_to_delete in ids_list_messages_to_delete:
                    try:
                        await call.bot.delete_message(call.message.chat.id, id_message_to_delete)
                    except Exception as err:
                        logger.exception('%s: %s', type(err), err)
            await call.message.answer_photo(photo=item.item_photos[0], caption=UserTexts.item_text(item),
                                            reply_markup=markup)
            await state.reset_data()
    else:
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO,
                                            UserTexts.user_products_out_of_stock_while_change(item_id),
                                            reply_markup=await categories_keyboard(call))


async def get_data_for_add_item_to_basket(call: CallbackQuery, callback_data: dict) -> typing.Tuple[Item, int, int,
                                                                                                    int]:
    telegram_id = int(callback_data.get('telegram_id'))
    item_id = int(callback_data.get('item_id'))
    quantity = int(callback_data.get('quantity'))
    item = await get_item(call, item_id)
    return item, telegram_id, quantity, item_id


async def get_item_in_basket(obj: typing.Union[Message, CallbackQuery], telegram_id: int, item_id: int) -> \
        typing.Union[ItemInBasket, None]:
    db = get_db(obj)
    item_in_basket_record = await db.select_item_from_basket(telegram_id, item_id)
    if item_in_basket_record:
        item_in_basket = get_item_in_basket_data(item_in_basket_record)
        return item_in_basket
    return


async def action_if_not_excceeded_total_quantity(call: CallbackQuery, new_item_in_basket: ItemInBasket, quantity: int):
    await call.answer(cache_time=1)
    # await call.message.delete()
    if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
        adding_to_basket_text = UserTexts.user_successful_adding_to_basket(new_item_in_basket, quantity)
        await call.message.answer(adding_to_basket_text)
        markup = await categories_keyboard(call)
        await call.message.answer_photo(UserTexts.PHOTO_LOGO, UserTexts.USER_BACK_TO_CATALOG, reply_markup=markup)
        clear_basket_on_schedule(call, added_at=new_item_in_basket.added_at)


async def add_item_to_basket(call: CallbackQuery, callback_data: dict):
    item, telegram_id, quantity, item_id = await get_data_for_add_item_to_basket(call, callback_data)
    if item:
        db = get_db(call)
        items_from_basket = await db.select_items_from_basket(call.from_user.id)
        payload = await load_basket_payload(items_from_basket)
        if check_payload(payload) and check_price_list(list(items_from_basket)):
            added_at = datetime.datetime.utcnow()
            item_in_basket = await get_item_in_basket(call, telegram_id, item.item_id)
            if item_in_basket:
                new_quantity = quantity + item_in_basket.quantity
                if new_quantity <= item.item_total_quantity:
                    new_item_in_basket_record = await db.change_quantity_item_in_basket(telegram_id, item.item_id,
                                                                                        new_quantity, added_at)
                    new_item_in_basket = get_item_in_basket_data(new_item_in_basket_record)
                    await action_if_not_excceeded_total_quantity(call, new_item_in_basket, quantity)
                else:
                    await call.answer(UserTexts.user_unsuccessful_adding_to_basket(
                        item_in_basket, quantity, item.item_total_quantity),
                        show_alert=True)
            else:
                new_item_in_basket_record = await db.add_items_to_basket(telegram_id, item.item_id,
                                                                         quantity, added_at)
                new_item_in_basket = get_item_in_basket_data(new_item_in_basket_record)
                await action_if_not_excceeded_total_quantity(call, new_item_in_basket, quantity)
        else:
            await call.answer('Это максимальное количество товаров в корзине. Больше нельзя добавить товары. Вы '
                              'можете оплатить текущую "корзину" и вернуться к покупкам',
                              show_alert=True)
    else:
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO,
                                            UserTexts.user_products_out_of_stock_while_change(item_id),
                                            reply_markup=await categories_keyboard(call))


async def prepare_markup_for_basket(call: CallbackQuery):
    db = get_db(call)
    telegram_id = call.from_user.id
    items_in_basket_record = await db.select_items_from_basket(telegram_id)
    if items_in_basket_record:
        text = UserTexts.user_basket_title(call.from_user.full_name)
        index = 1
        total = 0
        basket_list_items = []
        for item_in_basket_record in items_in_basket_record:
            text += '\n'
            item_in_basket = get_item_in_basket_data(item_in_basket_record)
            text += UserTexts.user_basket_item(index, item_in_basket)
            total += item_in_basket.item_price * item_in_basket.quantity
            basket_list_items.append((index, item_in_basket.item_id))
            index += 1
        text += UserTexts.user_basket_summary(total)
        return text, basket_list_items
    else:
        text = UserTexts.USER_BASKET_CANCEL_AFTER_24_HOURS
        return text, list()


async def on_show_basket(call: CallbackQuery, text: str, basket_list_items):
    if basket_list_items:
        text += UserTexts.USER_BASKET_PAY_OR_CLEAR
        markup = edit_basket_markup(basket_list_items)
        # await call.message.delete()
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
            await call.message.answer(text, reply_markup=markup)
    else:
        text = text
        markup = await categories_keyboard(call)
        # await call.message.delete()
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO, caption=text, reply_markup=markup)


async def show_basket(call: CallbackQuery):
    await call.answer(cache_time=1)
    text, basket_list_items = await prepare_markup_for_basket(call)
    await on_show_basket(call, text, basket_list_items)


async def delete_item_from_basket(call: CallbackQuery, callback_data: dict):
    await call.answer(cache_time=1)
    db = get_db(call)
    item_id = int(callback_data.get('item_id'))
    await db.delete_item_from_basket(call.from_user.id, item_id)
    text, basket_list_items = await prepare_markup_for_basket(call)
    markup = edit_basket_markup(basket_list_items)
    if basket_list_items:
        text += UserTexts.user_basket_deleted_item(item_id) + ' ' + UserTexts.USER_BASKET_PAY_OR_CLEAR
        await call.message.edit_text(text, reply_markup=markup)
    else:
        markup = await categories_keyboard(call)
        # await call.message.delete()
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
            try:
                remove_clear_basket_job(call)
                text = UserTexts.user_basket_deleted_item(item_id) + ' ' + UserTexts.USER_BASKET_EMPTY
                await call.message.answer_photo(UserTexts.PHOTO_LOGO, caption=text, reply_markup=markup)
                # await call.message.edit_text(text, reply_markup=markup)
            except JobLookupError:
                text = UserTexts.USER_BASKET_CANCEL_AFTER_24_HOURS
                await call.message.answer_photo(UserTexts.PHOTO_LOGO, caption=text, reply_markup=markup)


async def cancel_basket(call: CallbackQuery):
    await call.answer(cache_time=1)
    db = get_db(call)
    markup = await categories_keyboard(call)
    goods = await db.select_items_from_basket(call.from_user.id)
    # await call.message.delete()
    if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
        if goods:
            text = UserTexts.USER_BASKET_CANCEL_WITH_GOODS
        else:
            text = UserTexts.USER_BASKET_CANCEL_WITHOUT_GOODS
        await call.message.answer_photo(UserTexts.PHOTO_LOGO, caption=text, reply_markup=markup)


async def clear_basket(call: CallbackQuery):
    await call.answer(cache_time=1)
    db = get_db(call)
    await db.delete_all_items_from_basket(call.from_user.id)
    markup = await categories_keyboard(call)
    # await call.message.delete()
    if await delete_message(call, logger, UserTexts.PHOTO_LOGO, UserTexts.USER_REBOOT_BOT):
        try:
            remove_clear_basket_job(call)
            await call.message.answer_photo(UserTexts.PHOTO_LOGO, caption=UserTexts.USER_BASKET_CANCEL_WITHOUT_GOODS,
                                            reply_markup=markup)
        except JobLookupError:
            await call.message.answer_photo(UserTexts.PHOTO_LOGO, caption=UserTexts.USER_BASKET_CANCEL_AFTER_24_HOURS,
                                            reply_markup=markup)


def register_user(dp: Dispatcher):
    dp.register_message_handler(create_start_link, ChatTypeFilter(types.ChatType.PRIVATE), Command('get_link'),
                                state="*")
    dp.register_message_handler(user_start, ChatTypeFilter(types.ChatType.PRIVATE), CommandStart(), state="*")
    dp.register_callback_query_handler(back_to_main_menu, main_menu_cd.filter(button='main_menu'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_message_handler(user_help, ChatTypeFilter(types.ChatType.PRIVATE), CommandHelp(), state="*")
    dp.register_callback_query_handler(user_help, main_menu_cd.filter(button='help'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_message_handler(show_store_menu, ChatTypeFilter(types.ChatType.PRIVATE), Command('menu'), state="*")
    dp.register_callback_query_handler(show_store_menu, main_menu_cd.filter(button='catalog'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(about_us, main_menu_cd.filter(button='about_us'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(legal_information, main_menu_cd.filter(button='legal_information'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(navigate, menu_cd.filter(), ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(increase_quantity, edit_quantity_cd.filter(increase_or_decrease='increase'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(decrease_quantity, edit_quantity_cd.filter(increase_or_decrease='decrease'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(scroll_items_right, scroll_items_cd.filter(towards='right'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(scroll_items_left, scroll_items_cd.filter(towards='left'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(more_photos, more_photos_cd.filter(action='show'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(back_to_main_photo, more_photos_cd.filter(action='back'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(add_item_to_basket, add_to_basket_cd.filter(),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(show_basket, basket_cd.filter(action='show_basket'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(delete_item_from_basket, basket_cd.filter(action='delete'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(cancel_basket, basket_cd.filter(action='cancel'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
    dp.register_callback_query_handler(clear_basket, basket_cd.filter(action='cleare_basket'),
                                       ChatTypeFilter(types.ChatType.PRIVATE), state="*")
