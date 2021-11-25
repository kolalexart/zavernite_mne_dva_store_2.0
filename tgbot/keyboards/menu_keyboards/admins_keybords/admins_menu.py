import typing

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

cancel_keyboard_button = KeyboardButton(text='Отмена')
default_keyboard_button = KeyboardButton(text='По умолчанию')

ADMINS_MENU_OPTIONS = ['Добавить товар', 'Изменить товар', 'Удалить категорию товаров',
                       'Изменить название категории товаров', 'Удалить подкатегорию товаров',
                       'Изменить название подкатегории товаров']

ADMINS_CHANGE_ITEM_MENU = {'ID': 'ID',
                           'item_name': 'Название',
                           'item_photos': 'Фотографии',
                           'item_main_photo': 'Главное фото',
                           'item_price': 'Цену',
                           'item_description': 'Описание',
                           'item_short_description': 'Короткое описание',
                           'item_total_quantity': 'Количество',
                           'item_discontinued': 'Видимость',
                           'item_photo_url': 'Ссылку на фото для быстрого просмотра',
                           'item_delete': 'Удалить товар',
                           'cancel': 'Отменить изменение'}


change_item_cd = CallbackData('change_item', 'target', 'item_id')


def admins_menu_markup() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for option in ADMINS_MENU_OPTIONS:
        markup.insert(KeyboardButton(text=option))
    markup.row(cancel_keyboard_button)
    return markup


def choose_item_id_markup() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.insert(KeyboardButton(text='По умолчанию'))
    markup.row(cancel_keyboard_button)
    return markup


def choose_item_category_name_markup(list_categories: typing.Optional[typing.List[typing.Tuple[str, int]]] =
                                     None) -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if list_categories:
        list_categories_names = [category[0] for category in list_categories]
        for category_name in list_categories_names:
            markup.insert(KeyboardButton(text=category_name))
    markup.row(cancel_keyboard_button)
    return markup


def choose_item_subcategory_name_markup(list_subcategories: typing.Optional[typing.List[typing.Tuple[str, int]]] =
                                        None,
                                        without_subcategory_btn: typing.Optional[bool] = False) -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if list_subcategories:
        list_subcategories_names = [subcategory[0] for subcategory in list_subcategories]
        for subcategory_name in list_subcategories_names:
            if subcategory_name is None:
                markup.insert('Без подкатегории')
            else:
                markup.insert(KeyboardButton(text=subcategory_name))
    if without_subcategory_btn:
        markup.row(KeyboardButton('Без подкатегории'))
    markup.row(cancel_keyboard_button)
    return markup


def cancel_markup() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(cancel_keyboard_button)
    return markup


def yes_no_reply_markup() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(KeyboardButton(text='Да'), KeyboardButton(text='Нет'))
    markup.row(cancel_keyboard_button)
    return markup


def item_short_description_markup() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(KeyboardButton(text='Не требуется'))
    markup.row(cancel_keyboard_button)
    return markup


def item_discontinued_status_markup() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(KeyboardButton(text='Видимый'), KeyboardButton(text='Не видимый'))
    markup.row(cancel_keyboard_button)
    return markup


def choose_item_markup(items_list: typing.List[typing.Tuple[str, int]]) -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    for item_name, item_id in items_list:
        text = f'{item_name}'
        markup.insert(KeyboardButton(text=text))
    markup.row(cancel_keyboard_button)
    return markup


def admins_change_menu_markup(item_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    for target, text in ADMINS_CHANGE_ITEM_MENU.items():
        if text in [ADMINS_CHANGE_ITEM_MENU['item_photo_url'], ADMINS_CHANGE_ITEM_MENU['item_delete'],
                    ADMINS_CHANGE_ITEM_MENU['cancel']]:
            markup.row(InlineKeyboardButton(text=text, callback_data=change_item_cd.new(target=target,
                                                                                        item_id=item_id)))
        else:
            markup.insert(InlineKeyboardButton(text=text, callback_data=change_item_cd.new(target=target,
                                                                                           item_id=item_id)))
    return markup
