import typing

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.utils.callback_data import CallbackData

from tgbot.db_api.postgres_db import Database
from tgbot.keyboards.inline import main_menu_cd
from tgbot.misc.secondary_functions import get_db, Item, get_item_data

menu_cd = CallbackData('show_menu', 'level', 'item_category_code', 'item_subcategory_code', 'item_id')
buy_item = CallbackData('buy', 'item_id', 'quantity')
scroll_items_cd = CallbackData('scroll', 'towards', 'item_id', 'item_category_code', 'item_subcategory_code')
edit_quantity_cd = CallbackData('edit_quantity', 'increase_or_decrease', 'item_id', 'quantity')
add_to_basket_cd = CallbackData('add_to_basket', 'telegram_id', 'item_id', 'quantity')
basket_cd = CallbackData('basket', 'action', 'item_id')
more_photos_cd = CallbackData('more_photos', 'action', 'item_id')


def make_callback_data(level, item_category_code=0, item_subcategory_code: typing.Optional[int] = 0, item_id=0):
    if item_subcategory_code is None:
        item_subcategory_code = 0
    return menu_cd.new(level=level, item_category_code=item_category_code, item_subcategory_code=item_subcategory_code,
                       item_id=item_id)


def make_scroll_items_cd(towards: str, item_id: int, item_category_code: int,
                         item_subcategory_code: typing.Optional[int] = 0):
    if item_subcategory_code is None:
        item_subcategory_code = 0
    return scroll_items_cd.new(towards=towards, item_id=item_id, item_category_code=item_category_code,
                               item_subcategory_code=item_subcategory_code)


async def exist_subcategories(db: Database, item_category_code: int) -> bool:
    item_subcategory_names_list = [(list(i)[0]) for i in await db.get_subcategories_from_items(item_category_code)]
    return any(item_subcategory_names_list)


async def categories_keyboard(obj: typing.Union[Message, CallbackQuery]):
    db = get_db(obj)

    CURRENT_LEVEL = 0

    markup = InlineKeyboardMarkup(row_width=2)
    item_categories = await db.get_categories_from_items()

    if item_categories:
        for item_category_record in item_categories:
            item_category_name = dict(item_category_record).get('item_category_name')
            item_category_code = dict(item_category_record).get('item_category_code')
            # number_of_items = await db.count_items(item_category_code)
            button_text = f"{item_category_name}"

            if await exist_subcategories(db, item_category_code):
                callback_data = make_callback_data(level=CURRENT_LEVEL+1,
                                                   item_category_code=item_category_code)
                markup.insert(InlineKeyboardButton(text=button_text, callback_data=callback_data))
            else:
                button_text = f"{item_category_name}"
                callback_data = make_callback_data(level=CURRENT_LEVEL + 2,
                                                   item_category_code=item_category_code,
                                                   item_subcategory_code=None)
                markup.insert(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    markup.row(InlineKeyboardButton(text='Быстрый просмотр всех товаров',
                                    switch_inline_query_current_chat=''))
    markup.row(InlineKeyboardButton(text='В главное меню', callback_data=main_menu_cd.new(button='main_menu')))

    await check_on_basket_button(obj, markup)

    return markup


async def subcategories_keyboard(call: CallbackQuery, item_category_code: int):
    db = get_db(call)

    CURRENT_LEVEL = 1

    markup = InlineKeyboardMarkup(row_width=2)
    item_subcategories = await db.get_subcategories_from_items(item_category_code)

    for item_subcategory_record in item_subcategories:
        item_subcategory_name = dict(item_subcategory_record).get('item_subcategory_name')
        item_subcategory_code = dict(item_subcategory_record).get('item_subcategory_code')
        # number_of_items = await db.count_items(item_category_code=item_category_code,
        #                                        item_subcategory_code=item_subcategory_code)
        button_text = f"{item_subcategory_name}"
        callback_data = make_callback_data(level=CURRENT_LEVEL+1,
                                           item_category_code=item_category_code,
                                           item_subcategory_code=item_subcategory_code)
        markup.insert(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    await check_on_basket_button(call, markup)

    markup.row(InlineKeyboardButton(text='Назад', callback_data=make_callback_data(level=CURRENT_LEVEL - 1)))

    return markup


async def items_keyboard(call: CallbackQuery, item_category_code: int, item_subcategory_code: int):
    db = get_db(call)

    CURRENT_LEVEL = 2

    markup = InlineKeyboardMarkup(row_width=2)
    items = await db.get_items_from_items(item_category_code, item_subcategory_code)

    for item_record in items:
        item = get_item_data(item_record)
        button_text = f'{item.item_name}'
        callback_data = make_callback_data(level=CURRENT_LEVEL+1,
                                           item_category_code=item_category_code,
                                           item_subcategory_code=item_subcategory_code,
                                           item_id=item.item_id)
        markup.insert(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    await check_on_basket_button(call, markup)

    if await exist_subcategories(db, item_category_code):
        markup.row(InlineKeyboardButton(text='Назад',
                                        callback_data=make_callback_data(level=CURRENT_LEVEL - 1,
                                                                         item_category_code=item_category_code)))
    else:
        markup.row(InlineKeyboardButton(text='Назад', callback_data=make_callback_data(level=CURRENT_LEVEL - 2)))

    return markup


async def item_keyboard(call: CallbackQuery, item: Item, quantity: int):

    CURRENT_LEVEL = 3

    markup = InlineKeyboardMarkup(row_width=3)

    markup.row(InlineKeyboardButton(text='Больше фото',
                                    callback_data=more_photos_cd.new(
                                        action='show',
                                        item_id=item.item_id
                                    )))

    markup.row(InlineKeyboardButton(text='⬅',
                                    callback_data=make_scroll_items_cd(
                                        towards='left',
                                        item_id=item.item_id,
                                        item_category_code=item.item_category_code,
                                        item_subcategory_code=item.item_subcategory_code)),
               InlineKeyboardButton(text='➡',
                                    callback_data=make_scroll_items_cd(
                                        towards='right',
                                        item_id=item.item_id,
                                        item_category_code=item.item_category_code,
                                        item_subcategory_code=item.item_subcategory_code)))

    # markup.row(InlineKeyboardButton(text='⬇',
    #                                 callback_data=edit_quantity_cd.new(increase_or_decrease='decrease',
    #                                                                    item_id=item.item_id,
    #                                                                    quantity=quantity)),
    #            InlineKeyboardButton(text='⬆',
    #                                 callback_data=edit_quantity_cd.new(increase_or_decrease='increase',
    #                                                                    item_id=item.item_id,
    #                                                                    quantity=quantity)))

    markup.row(InlineKeyboardButton(text='⬇',
                                    callback_data=edit_quantity_cd.new(increase_or_decrease='decrease',
                                                                       item_id=item.item_id,
                                                                       quantity=quantity)),
               InlineKeyboardButton(text=f'Купить {quantity} шт.\n'
                                         f'Доступно {item.item_total_quantity} шт.',
                                    callback_data=buy_item.new(item_id=item.item_id,
                                                               quantity=quantity)),
               InlineKeyboardButton(text='⬆',
                                    callback_data=edit_quantity_cd.new(increase_or_decrease='increase',
                                                                       item_id=item.item_id,
                                                                       quantity=quantity)))

    markup.row(InlineKeyboardButton(text=f'Добавить в 🧺 {quantity} шт.',
                                    callback_data=add_to_basket_cd.new(telegram_id=call.from_user.id,
                                                                       item_id=item.item_id,
                                                                       quantity=quantity)))

    await check_on_basket_button(call, markup)

    markup.row(InlineKeyboardButton(text='Отправить ссылку на магазин',
                                    switch_inline_query=''))

    markup.row(InlineKeyboardButton(text='Назад',
                                    callback_data=make_callback_data(level=CURRENT_LEVEL-1,
                                                                     item_category_code=item.item_category_code,
                                                                     item_subcategory_code=item.item_subcategory_code)))
    return markup


async def check_on_basket_button(obj: typing.Union[CallbackQuery, Message], markup: InlineKeyboardMarkup):
    db = get_db(obj)
    telegram_id = obj.from_user.id
    if await db.select_items_from_basket(telegram_id):
        button = InlineKeyboardButton(text=f'Перейти в 🧺',
                                      callback_data=basket_cd.new(action='show_basket', item_id=0))
        markup.row(button)


def back_button_keyboard_for_more_photos(item_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=more_photos_cd.new(action='back', item_id=item_id))]])
    return markup


def edit_basket_markup(basket_list_items: typing.List[typing.Tuple[int, int]]):
    markup = InlineKeyboardMarkup(row_width=5)

    if basket_list_items:
        for index, item_id in basket_list_items:
            markup.insert(InlineKeyboardButton(text=str(index),
                                               callback_data=basket_cd.new(action='delete',
                                                                           item_id=item_id)))

        markup.row(InlineKeyboardButton(text='Очистить корзину',
                                        callback_data=basket_cd.new(action='cleare_basket',
                                                                    item_id=0)))

        markup.row(InlineKeyboardButton(text='Оплатить', callback_data=buy_item.new(item_id='basket',
                                                                                    quantity='different')))

    markup.row(InlineKeyboardButton(text='Выйти',
                                    callback_data=basket_cd.new(action='cancel',
                                                                item_id=0)))
    return markup

