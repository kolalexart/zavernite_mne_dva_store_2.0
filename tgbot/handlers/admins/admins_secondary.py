import typing
from io import BytesIO
from logging import Logger
from re import Pattern

import aiohttp
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, PhotoSize, ContentType, ReplyKeyboardRemove

from tgbot.misc.secondary_functions import get_db, get_item_data, Item, ItemPatterns
from tgbot.services.integrations.telegraph.exceptions import TelegraphAPIError
from tgbot.services.integrations.telegraph.service import TelegraphService
from tgbot.services.integrations.telegraph.types import UploadedFile


class ExceededMaxProductsQuantity(Exception):
    pass


class ExceededMaxProductCategoryQuantity(Exception):
    pass


class ExceededMaxProductSubCategoryQuantity(Exception):
    pass


admin_filters = dict(content_types=[ContentType.ANY], is_admin=True)


async def get_items_categories(message: Message) -> typing.Union[typing.List[typing.Tuple[str, int]], None]:
    db = get_db(message)
    categories_records = await db.get_categories_from_items(for_admins=True)
    list_categories = []
    if categories_records:
        for category_record in categories_records:
            item_category_name = dict(category_record).get('item_category_name')
            item_category_code = dict(category_record).get('item_category_code')
            list_categories.append((item_category_name, item_category_code))
        return list_categories
    else:
        return


async def get_items_subcategories(message: Message, item_category_code: int) -> \
        typing.Union[typing.List[typing.Tuple[str, int]], None]:
    db = get_db(message)
    subcategories_records = await db.get_subcategories_from_items(item_category_code, for_admis=True)
    list_subcategories = []
    if subcategories_records:
        for subcategory_record in subcategories_records:
            item_subcategory_name = dict(subcategory_record).get('item_subcategory_name')
            item_subcategory_code = dict(subcategory_record).get('item_subcategory_code')
            list_subcategories.append((item_subcategory_name, item_subcategory_code))
        return list_subcategories
    else:
        return


def choose_default_item_id(list_items_ids: typing.List[int]) -> int:

    if not list_items_ids:
        return 1

    if list_items_ids[0] != 1:
        return 1

    for index in range(1, len(list_items_ids)):
        delta = list_items_ids[index] - list_items_ids[index - 1]
        if delta == 1:
            continue
        else:
            return list_items_ids[index - 1] + 1

    item_id = max(list_items_ids) + 1
    if item_id > 9999:
        raise ExceededMaxProductsQuantity('Максимальное количество товаров 9999. Лимит закончен. '
                                          'Больше товаров создать нельзя')
    else:
        return item_id


def choose_category_code_number(list_categories: typing.Union[typing.List[typing.Tuple[str, int]], None]) -> int:

    if not list_categories:
        return 1000

    item_category_codes = sorted([category[1] for category in list_categories])

    if item_category_codes[0] != 1000:
        return 1000

    for index in range(1, len(item_category_codes)):
        delta = item_category_codes[index] - item_category_codes[index - 1]
        if delta == 1:
            continue
        else:
            return item_category_codes[index - 1] + 1

    category_number = max(item_category_codes) + 1
    if category_number > 9999:
        raise ExceededMaxProductCategoryQuantity('Максимальный номер категории товара 9999. Лимит закончен. '
                                                 'Больше новых категорий создать нельзя')
    else:
        return category_number


def choose_subcategory_code_number(list_subcategories: typing.Union[typing.List[typing.Tuple[str, int]], None],
                                   item_category_code: int) -> int:
    if not list_subcategories:
        return item_category_code * 10

    item_subcategory_codes = sorted([subcategory[1] for subcategory in list_subcategories])

    if item_subcategory_codes[0] != item_category_code * 10:
        return item_category_code * 10

    for index in range(1, len(item_subcategory_codes)):
        delta = int(str(item_subcategory_codes[index])[4:]) - int(str(item_subcategory_codes[index - 1])[4:])
        if delta == 1:
            continue
        else:
            return int(str(item_category_code) + str(int(str(item_subcategory_codes[index - 1])[4:]) + 1))

    item_subcategory_codes_without_prefix = [int(str(item_subcategory_code)[4:]) for item_subcategory_code in
                                             item_subcategory_codes]
    prefix = str(item_category_code)
    subcategory_number_without_prefix = max(item_subcategory_codes_without_prefix) + 1
    subcategory_number = int(prefix + str(subcategory_number_without_prefix))
    max_subcategory_number = int(prefix + str(9999))
    if subcategory_number > max_subcategory_number:
        raise ExceededMaxProductSubCategoryQuantity(f'Максимальный номер категории товара {max_subcategory_number}. '
                                                    f'Лимит закончен. Больше новых подкатегорий создать нельзя')
    else:
        return subcategory_number


async def check_on_items_limits_in_category(message: Message, item_category_code: int) -> bool:
    db = get_db(message)
    items_quantity = await db.count_items(item_category_code)
    return True if items_quantity < 98 else False


async def check_on_items_limits_in_subcategory(message: Message, item_category_code: int,
                                               item_subcategory_code: int) -> bool:
    db = get_db(message)
    items_quantity = await db.count_items(item_category_code, item_subcategory_code)
    return True if items_quantity < 98 else False


async def check_on_categories_limits(message) -> bool:
    db = get_db(message)
    categories_quantity = await db.count_categories()
    return True if categories_quantity < 97 else False


async def check_on_subcategories_limits(message: Message, item_category_code: int) -> bool:
    db = get_db(message)
    subcategories_quantity = await db.count_subcategories(item_category_code)
    return True if subcategories_quantity < 98 else False


async def get_data_from_state(state: FSMContext, *args: str) -> list:
    data_from_state = await state.get_data()
    data_list = list()
    for arg in args:
        data = data_from_state.get(arg)
        data_list.append(data)
    return data_list


def get_chosen_category_code(category_name: str, list_categories: typing.List[typing.Tuple[str, int]]) -> int:
    for item_category_name, item_category_code in list_categories:
        if item_category_name.lower() == category_name.lower():
            return item_category_code


def get_chosen_item_id(name: str, items_list: typing.List[typing.Tuple[str, int]]) -> int:
    for item_name, item_id in items_list:
        if item_name.lower() == name.lower():
            return item_id


def check_on_without_subcategory(list_subcategories: typing.List[typing.Union[typing.Tuple[str, int],
                                                                              typing.Tuple[None, None]]]) -> bool:
    if len(list_subcategories) == 1:
        return list_subcategories[0][0] is None and list_subcategories[0][1] is None
    return False


async def reject_content_type(message: Message, additional_text: typing.Optional[str],
                              reply_markup: ReplyKeyboardMarkup):
    content_type = message.content_type
    text = f'🔴 Здесь нельзя присылать тип данных <b>"{content_type}"</b>. '
    if additional_text:
        text += additional_text
    await message.answer(text, reply_markup=reply_markup)


async def get_photo_link(message: Message) -> str:
    bot = message.bot
    photo: PhotoSize = message.photo[-1]
    with await photo.download(BytesIO()) as file:
        form = aiohttp.FormData()
        form.add_field(
            name='file',
            value=file,
        )
        async with bot.session.post('https://telegra.ph/upload', data=form) as response:
            img_src = await response.json()
    link = 'https://telegra.ph' + img_src[0].get('src')
    return link


async def on_process_upload_photo(message: Message, logger: Logger, state: FSMContext, err_text: str,
                                  file_uploader: TelegraphService,
                                  markup: typing.Optional[ReplyKeyboardMarkup] = ReplyKeyboardRemove()) -> \
        typing.Optional[UploadedFile]:
    try:
        uploaded_photo = await file_uploader.upload_photo(message.photo[-1])
    except TelegraphAPIError as err:
        logger.exception('Проблема на стороне Telegraph. В данный момент нельзя загрузить фото в Telegraph. '
                         'Попробуйте позже.\n%s: %s', type(err), err)
        await state.finish()
        await message.answer(err_text, reply_markup=markup)
        return
    else:
        return uploaded_photo


async def get_items_list(message: Message, item_category_code: int,
                         item_subcategory_code: typing.Optional[int] = None) -> typing.List[typing.Tuple[str, int]]:
    db = get_db(message)
    items_list = []
    item_records = await db.get_items_from_items(item_category_code, item_subcategory_code, for_admins=True)
    for item_record in item_records:
        item = get_item_data(item_record)
        items_list.append((item.item_name, item.item_id))
    return items_list


def full_gproduct_description(item: Item):
    text = f'<b>ID:</b> {item.item_id}\n\n'\
           f'<b>Категория:</b> {item.item_category_name}\n\n'\
           f'<b>Код категории:</b> {item.item_category_code}\n\n'\
           f'<b>Подкатегория:</b> {subcategory_name_or_code(item.item_subcategory_name)}\n\n'\
           f'<b>Код подкатегории:</b> {subcategory_name_or_code(item.item_subcategory_code)}\n\n'\
           f'<b>Название товара:</b> {item.item_name}\n\n'\
           f'<b>Количество фотографий:</b> {len(item.item_photos)}\n\n'\
           f'<b>Стоимость товара:</b> {item.item_price}\n\n'\
           f'<b>Описание товара:</b>\n'\
           f'<i>{item.item_description}</i>\n\n'\
           f'<b>Короткое описание товара:</b> {item.item_short_description}\n\n'\
           f'<b>Количество товара на складе:</b> {item.item_total_quantity}\n\n'\
           f'<b>Видимость товара:</b> {visibility(item.item_discontinued)}\n\n'\
           f'<b>Ссылка на фото для быстрого просмотра:</b> {item.item_photo_url}'
    return text


def visibility(item_discontinued: bool) -> str:
    return 'Не видимый' if item_discontinued else 'Видимый'


def subcategory_name_or_code(item_subcategory: typing.Union[str, int, None]):
    if item_subcategory:
        return item_subcategory
    else:
        return 'Без подкатегории'


# def convert_to_text_short_description(item_short_description: typing.Union[str, None]):
#     return item_short_description if item_short_description else "Не требуется"


def is_requerid_format_item_id(message: Message, used_ids: typing.List[int]) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_ID
        if pattern.match(message.text):
            item_id = int(message.text)
            if item_id not in used_ids:
                return True
    return False


def is_requerid_format_item_name(message: Message, used_names: typing.List[str]) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_NAME
        if pattern.match(message.text):
            item_name = message.text
            if item_name.lower() not in used_names:
                return True
    return False


def is_requerid_format_media_group(messages: typing.List[Message]) -> bool:
    for message in messages:
        if message.content_type != ContentType.PHOTO:
            return False
    return True


def is_requerid_format_item_photo(message: Message) -> bool:
    return message.content_type == ContentType.PHOTO


def is_requerid_format_item_price(message: Message) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_PRICE
        if pattern.match(message.text):
            return True
    return False


def is_requerid_format_item_description(message: Message) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_DESCRIPTION
        if pattern.match(message.text):
            return True
    return False


def is_requerid_format_item_short_description(message: Message) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_SHORT_DESCRIPTION
        if pattern.match(message.text):
            return True
    return False


def is_requerid_format_item_total_quantity(message: Message) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_TOTAL_QUANTITY
        if pattern.match(message.text):
            return True
    return False


def is_requerid_format_item_discontinued(message: Message) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_NAME
        if pattern.match(message.text):
            item_discontinued = message.text.lower()
            if item_discontinued in ['видимый', 'не видимый']:
                return True
    return False


def is_requerid_format_item_photo_url(message: Message) -> bool:
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_PHOTO_URL
        if pattern.match(message.text):
            return True
    return False


def is_requerid_format_yes_or_no_markup(message: Message) -> bool:
    if message.content_type == ContentType.TEXT:
        confirmation = message.text.lower()
        if confirmation in ['да', 'нет']:
            return True
    return False


def is_requerid_format_item_category(message: Message,
                                     list_categories: typing.Union[typing.List[typing.Tuple[str, int]], None]) -> bool:
    if message.content_type == ContentType.TEXT:
        item_category_name = message.text.lower()
        list_item_categories_names = [category[0].lower() for category in list_categories]
        if item_category_name in list_item_categories_names:
            return True
    return False


def get_name_and_code(message: Message, list_categories: typing.Union[typing.List[typing.Tuple[str, int]], None]) -> \
        typing.Union[typing.Tuple[str, int], None]:
    for item_category_name, item_category_code in list_categories:
        if item_category_name.lower() == message.text.lower():
            return item_category_name, item_category_code
    return None


async def is_requerid_format_item_category_while_renaiming(message: Message, list_categories: list,
                                                           pattern: Pattern) -> bool:
    if message.content_type == ContentType.TEXT:
        if pattern.match(message.text):
            item_category_name = message.text.lower()
            list_item_categories_names = [category[0].lower() for category in list_categories]
            if item_category_name not in list_item_categories_names:
                return True
    return False
