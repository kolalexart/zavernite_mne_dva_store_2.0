import logging
import typing

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, MediaGroup, \
    InputMediaPhoto, ContentType, CallbackQuery
from asyncpg import ForeignKeyViolationError, Record

from tgbot.handlers.admins.admins_secondary import admin_filters, get_data_from_state, \
    get_items_subcategories, get_chosen_category_code, check_on_without_subcategory, get_items_list, \
    get_chosen_item_id, full_gproduct_description, reject_content_type, is_requerid_format_item_id, \
    is_requerid_format_item_name, is_requerid_format_media_group, is_requerid_format_item_photo, \
    is_requerid_format_item_price, is_requerid_format_item_description, is_requerid_format_item_total_quantity, \
    visibility, is_requerid_format_item_discontinued, is_requerid_format_item_photo_url, \
    is_requerid_format_yes_or_no_markup, is_requerid_format_item_short_description, on_process_upload_photo
from tgbot.handlers.user import get_item
from tgbot.keyboards.menu_keyboards.admins_keybords.admins_menu import choose_item_category_name_markup, \
    choose_item_subcategory_name_markup, choose_item_markup, admins_change_menu_markup, cancel_markup, change_item_cd, \
    ADMINS_CHANGE_ITEM_MENU, item_discontinued_status_markup, yes_no_reply_markup, item_short_description_markup
from tgbot.middlewares.album import album_latency
from tgbot.misc.secondary_functions import Item, get_db, delete_message_for_admins
from tgbot.misc.states import ChangeItem
from tgbot.services.integrations.telegraph.service import TelegraphService

logger = logging.getLogger(__name__)


async def change_choose_item_category(message: Message, state: FSMContext):
    list_categories = (await get_data_from_state(state, 'list_categories'))[0]
    if message.content_type == ContentType.TEXT:
        item_category_name = message.text
        list_item_categories_names = [category[0].lower() for category in list_categories]
        if item_category_name.lower() in list_item_categories_names:
            item_category_code = get_chosen_category_code(item_category_name, list_categories)
            list_subcategories = await get_items_subcategories(message, item_category_code)
            if list_subcategories and check_on_without_subcategory(list_subcategories):
                items_list = await get_items_list(message, item_category_code)
                await message.answer(f'Вы выбрали категорию <b>{item_category_name}</b>, в которой нет подкатегорий. '
                                     f'Выберите товар, который хотите изменить:',
                                     reply_markup=choose_item_markup(items_list))
                await state.update_data(item_category_name=item_category_name,
                                        item_category_code=item_category_code,
                                        items_list=items_list)
                await ChangeItem.item_name_choose.set()
            else:
                await message.answer(f'Вы выбрали категорию <b>{item_category_name}</b>. Выберите подкатегорию, в '
                                     f'которой хотите изменить товар',
                                     reply_markup=choose_item_subcategory_name_markup(list_subcategories))
                await state.update_data(item_category_name=item_category_name,
                                        item_category_code=item_category_code,
                                        list_subcategories=list_subcategories)
                await ChangeItem.item_subcategory_name.set()
        else:
            await message.answer(f'Категории <b>{item_category_name}</b> не существует, попробуйте еще раз или '
                                 f'отмените операцию',
                                 reply_markup=choose_item_category_name_markup(list_categories))
    else:
        additional_text = 'Пожалуйста, пришлите название существующей категории'
        await reject_content_type(message, additional_text, choose_item_category_name_markup(list_categories))


async def change_choose_item_subcategory(message: Message, state: FSMContext):
    item_category_name, item_category_code, list_subcategories = \
        await get_data_from_state(state, 'item_category_name', 'item_category_code', 'list_subcategories')
    if message.content_type == ContentType.TEXT:
        item_subcategory_name = message.text
        item_subcategory_code = get_chosen_category_code(item_subcategory_name, list_subcategories)
        list_subcategories_names = [subcategory[0].lower() for subcategory in list_subcategories]
        items_list = await get_items_list(message, item_category_code, item_subcategory_code)
        if item_subcategory_name.lower() in list_subcategories_names:
            await message.answer(f'Вы выбрали подкатегорию <b>{item_subcategory_name}</b>. Выберите товар, который '
                                 f'хотите изменить:',
                                 reply_markup=choose_item_markup(items_list))
            await state.update_data(item_subcategory_name=item_subcategory_name,
                                    item_subcategory_code=item_subcategory_code,
                                    items_list=items_list)
            await ChangeItem.item_name_choose.set()
        else:
            await message.answer(f'В категории <b>{item_category_name}</b> нет подкатегории '
                                 f'<b>{item_subcategory_name}</b>. Попробуйте еще раз или отмените операцию',
                                 reply_markup=choose_item_subcategory_name_markup(list_subcategories))
    else:
        additional_text = f'Пожалуйста, пришлите название подтегории, существующей в ' \
                          f'категории <b>{item_category_name}</b>'
        await reject_content_type(message, additional_text, choose_item_subcategory_name_markup(list_subcategories))


async def answer_photo_or_media_group(message: Message, item: Item, caption: str, markup):
    if len(item.item_photos) == 1:
        await message.answer_photo(photo=item.item_photos[0], caption=caption, reply_markup=markup)
    else:
        media_group = MediaGroup()
        for photo in item.item_photos:
            input_media_photo = InputMediaPhoto(media=photo)
            media_group.attach_photo(input_media_photo)
        await message.answer_media_group(media_group)
        await message.answer(caption, reply_markup=markup)


async def change_choose_item_name(message: Message, state: FSMContext):
    items_list, item_category_name, item_subcategory_name = \
        await get_data_from_state(state, 'items_list', 'item_category_name', 'item_subcategory_name')
    item_names_list = [item[0].lower() for item in items_list]
    if message.content_type == ContentType.TEXT:
        item_name = message.text
        if item_name.lower() in item_names_list:
            item_id = get_chosen_item_id(item_name, items_list)
            item = await get_item(message, item_id)
            caption = '⬆⬆⬆ Вы изменяете этот товар'
            await answer_photo_or_media_group(message, item, caption, ReplyKeyboardRemove())
            text = 'Сейчас у товара следующие характеристики:\n\n' + full_gproduct_description(item)
            text += '\n\nИзменить категорию или подкатегорию товара можно только удалив товар и создав его ' \
                    'заново.\n\nЧто будем менять?'
            await message.answer(text, reply_markup=admins_change_menu_markup(item.item_id),
                                 disable_web_page_preview=True)
            await state.finish()
        else:
            if item_subcategory_name:
                await message.answer(f'Товара с названием <b>{item_name}</b> в категории <b>{item_category_name}</b> в '
                                     f'подкатегории <b>{item_subcategory_name}</b> не существует. Попробуйте еще раз '
                                     f'или отмените операцию',
                                     reply_markup=choose_item_markup(items_list))
            else:
                await message.answer(f'Товара с названием <b>{item_name}</b> в категории <b>{item_category_name}</b> '
                                     f'не существует. Попробуйте еще раз или отмените операцию',
                                     reply_markup=choose_item_markup(items_list))
    else:
        if item_subcategory_name:
            additional_text = f'Пожалуйста, пришли название товара, существующего в категории ' \
                              f'<b>{item_category_name}</b> в подкатегории <b>{item_subcategory_name}</b>:'
        else:
            additional_text = f'Пожалуйста, пришли название товара, существующего в категории ' \
                              f'<b>{item_category_name}</b>:'
        await reject_content_type(message, additional_text, choose_item_markup(items_list))


async def product_still_exists(target: typing.Union[CallbackQuery, Message], state: FSMContext,
                               item: typing.Optional[typing.Union[Item, Record]], item_id: int):
    message = target if isinstance(target, Message) else target.message
    if item:
        return True
    if isinstance(target, Message):
        await message.answer(f'Товар с "<b>ID {item_id}</b>" больше не существует', reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer(f'Товар с "<b>ID {item_id}</b>" больше не существует')
    await state.finish()
    return


async def changing_item_id(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    db = get_db(call)
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        list_item_ids = [item_id_record.get('item_id') for item_id_record in await db.get_items_ids_from_items()]
        item_ids_str = ', '.join(list(map(str, list_item_ids)))
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b>: {item.item_id}\n\n' \
               f'Пожалуйста, введите целое число в интервале от 1 до 9999 отличное от уже ' \
               f'использованных: {item_ids_str}. Либо отмените операцию'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id,
                                list_item_ids=list_item_ids,
                                item_ids_str=item_ids_str)
        await ChangeItem.item_id.set()


async def changing_item_name(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    db = get_db(call)
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        list_item_names = [item_name_record.get('item_name').lower() for item_name_record in
                           await db.get_items_names_from_items()]
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b>: {item.item_name}\n\n' \
               f'Пожалуйста, введите новое название товара, состоящее не более, чем из 30 символов и отличное от уже ' \
               f'имеющихся. Либо отмените операцию'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id,
                                list_item_names=list_item_names,
                                item_name=item.item_name)
        await ChangeItem.item_name_set.set()


async def changing_item_photos(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас у товара загружено фотографий: {len(item.item_photos)} шт.\n\n' \
               f'Пожалуйста, пришлите новые фотографии товара до 10 шт. Фотографии должны быть присланы ' \
               f'картинкой или группой фотографий. Либо отмените операцию'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id)
        await ChangeItem.item_photos.set()


async def changing_item_main_photo(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас у товара загружено фотографий: {len(item.item_photos)} шт.\n\n' \
               f'Пожалуйста, пришлите одно новое фото товара, которое будет установлено в качестве основного. ' \
               f'Либо отмените операцию'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id)
        await ChangeItem.item_main_photo.set()


async def changing_item_price(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b>: {item.item_price}\n\n' \
               f'Пожалуйста, пришлите цену товара в рублях. Цена должна быть без копеек и находиться в интервале от ' \
               f'10 до 1000000'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id, item_price=item.item_price)
        await ChangeItem.item_price.set()


async def changing_item_description(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b>:\n\n<i>{item.item_description}</i>\n\n' \
               f'Пожалуйста, введите новое описание товара, состоящее не более, чем из 800 символов. ' \
               f'Либо отмените операцию'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id,
                                item_description=item.item_description)
        await ChangeItem.item_description.set()


async def changing_item_short_description(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b>:\n\n<i>{item.item_short_description}</i>\n\n' \
               f'Пожалуйста, введите новое описание товара, состоящее не более, чем из 50 символов, нажмите ' \
               f'"Не требуется" либо отмените операцию'
        await call.message.answer(text, reply_markup=item_short_description_markup())
        await state.update_data(item_id=item_id,
                                item_short_description=item.item_short_description)
        await ChangeItem.item_short_description.set()


async def changing_item_total_quantity(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b>: {item.item_total_quantity}\n\n' \
               f'Пожалуйста, пришлите новое количество товара. Количество должно быть от ' \
               f'0 до 9999'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id, item_total_quantity=item.item_total_quantity)
        await ChangeItem.item_total_quantity.set()


async def changing_item_discontinued(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b>: {visibility(item.item_discontinued)}\n\n' \
               f'Пожалуйста, введите новый статус видимости товара:'
        await call.message.answer(text, reply_markup=item_discontinued_status_markup())
        await state.update_data(item_id=item_id, item_discontinued=item.item_discontinued)
        await ChangeItem.item_discontinued.set()


async def changing_item_photo_url(call: CallbackQuery, state: FSMContext, target: str, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы изменяете <b>{ADMINS_CHANGE_ITEM_MENU[target]}</b> товара <b>{item.item_name}</b>.\n\n' \
               f'Сейчас ссылка на фото для быстрого просмотрта и выставления счетов: {item.item_photo_url}\n\n' \
               f'Пожалуйста, пришлите одно новое фото товара, которое будет установлено для быстрого просмотра и ' \
               f'выствления счетов. Либо пришлите ссылку на фотографию на вашем сайте в формате .jpg или .jpeg, ' \
               f'начинающуюся на "http://" или "https://" и заканчивающуюся на ".jpeg" или ".jpg". Либо отмените ' \
               f'операцию'
        await call.message.answer(text, reply_markup=cancel_markup())
        await state.update_data(item_id=item_id, item_photo_url=item.item_photo_url)
        await ChangeItem.item_photo_url.set()


async def deleting_item(call: CallbackQuery, state: FSMContext, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'Вы собираетесь удалить товар <b>{item.item_name}</b> с ID {item.item_id}\n\n' \
               f'Вы уверены, что хотите его безвозвратно удалить?'
        await call.message.answer(text, reply_markup=yes_no_reply_markup())
        await state.update_data(item_id=item_id, item_name=item.item_name)
        await ChangeItem.item_delete.set()


async def cancel_changing_item(call: CallbackQuery, state: FSMContext, item_id: int):
    item = await get_item(call, item_id)
    if await product_still_exists(call, state, item, item_id):
        text = f'🟢 Вы успешно отменили изменение <b>{item.item_name}</b> с ID {item.item_id}\n\n'
        await state.finish()
        await call.message.answer(text)


async def start_changing_item_with_item_id(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await call.answer(cache_time=1)
    if await delete_message_for_admins(call, logger, state):
        # await call.message.delete()
        target = callback_data.get('target')
        item_id = int(callback_data.get('item_id'))
        if target == 'ID':
            await changing_item_id(call, state, target, item_id)
        elif target == 'item_name':
            await changing_item_name(call, state, target, item_id)
        elif target == 'item_photos':
            await changing_item_photos(call, state, target, item_id)
        elif target == 'item_main_photo':
            await changing_item_main_photo(call, state, target, item_id)
        elif target == 'item_price':
            await changing_item_price(call, state, target, item_id)
        elif target == 'item_description':
            await changing_item_description(call, state, target, item_id)
        elif target == 'item_short_description':
            await changing_item_short_description(call, state, target, item_id)
        elif target == 'item_total_quantity':
            await changing_item_total_quantity(call, state, target, item_id)
        elif target == 'item_discontinued':
            await changing_item_discontinued(call, state, target, item_id)
        elif target == 'item_photo_url':
            await changing_item_photo_url(call, state, target, item_id)
        elif target == 'item_delete':
            await deleting_item(call, state, item_id)
        elif target == 'cancel':
            await cancel_changing_item(call, state, item_id)


async def change_item_id(message: Message, state: FSMContext):
    list_items_ids, item_id, items_ids_str = await get_data_from_state(state, 'list_item_ids', 'item_id',
                                                                       'item_ids_str')
    if is_requerid_format_item_id(message, list_items_ids):
        item_id_new = int(message.text)
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_id', item_id_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 ID успешно изменен с <b>{item_id}</b> на '
                                 f'<b>{item_id_new}</b>', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, введите целое число в интервале от 1 до 9999 отличное от уже '\
               f'использованных: {items_ids_str}. Либо отмените операцию'
        await message.answer(text, reply_markup=cancel_markup())


async def change_item_name(message: Message, state: FSMContext):
    list_item_names, item_id, item_name = await get_data_from_state(state, 'list_item_names', 'item_id', 'item_name')
    if is_requerid_format_item_name(message, list_item_names):
        item_name_new = message.text.capitalize()
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_name', item_name_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Название товара успешно изменено c <b>{item_name}</b> на '
                                 f'<b>{item_name_new}</b>',
                                 reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, введите новое название товара, состоящее не более, чем из 30 символов и ' \
               f'отличное от уже имеющихся. Либо отмените операцию'
        await message.answer(text, reply_markup=cancel_markup())


@album_latency(latency=1)
async def change_item_photos(message: Message, state: FSMContext, album: typing.List[types.Message]):
    item_id = (await get_data_from_state(state, 'item_id'))[0]
    if is_requerid_format_media_group(album):
        item_photos_new = [message.photo[-1].file_id for message in album]
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_photos', item_photos_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Фотографии успешно изменены', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, пришлите новые фотографии товара до 10 шт. Другие форматы не принимаются. Фотографии ' \
               f'должны быть присланы картинкой или группой фотографий. Либо отмените операцию'
        await message.answer(text, reply_markup=cancel_markup())


async def change_item_photo(message: Message, state: FSMContext):
    item_id = (await get_data_from_state(state, 'item_id'))[0]
    if is_requerid_format_item_photo(message):
        item_photos_new = [message.photo[-1].file_id]
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_photos', item_photos_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Фотография успешно изменена', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, пришлите новые фотографии товара до 10 шт. Другие форматы не принимаются. Фотографии ' \
               f'должны быть присланы картинкой или группой фотографий. Либо отмените операцию'
        await message.answer(text, reply_markup=cancel_markup())


@album_latency(latency=1)
async def change_item_main_photo_group(message: Message):
    text = f'🔴 Пожалуйста, пришлите одно новое фото товара, которое будет установлено в качестве основного. ' \
           f'Либо отмените операцию'
    await message.answer(text, reply_markup=cancel_markup())


async def change_item_main_photo(message: Message, state: FSMContext):
    item_id = (await get_data_from_state(state, 'item_id'))[0]
    if is_requerid_format_item_photo(message):
        item_main_photo_new = message.photo[-1].file_id
        db = get_db(message)
        updated_item = await db.update_item_first_photo_from_items(item_id, item_main_photo_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Главное фото успешно изменено', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, пришлите одно новое фото товара, которое будет установлено в качестве основного. '\
               f'Либо отмените операцию'
        await message.answer(text, reply_markup=cancel_markup())


async def change_item_price(message: Message, state: FSMContext):
    item_id, item_price = await get_data_from_state(state, 'item_id', 'item_price')
    if is_requerid_format_item_price(message):
        item_price_new = int(message.text)
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_price', item_price_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Цена товара успешно изменена с <b>{item_price}</b> на '
                                 f'<b>{item_price_new}</b>', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, введите целое число от 10 до 1000000'
        await message.answer(text, reply_markup=cancel_markup())


async def change_item_description(message: Message, state: FSMContext):
    item_id, item_description = await get_data_from_state(state, 'item_id', 'item_description')
    if is_requerid_format_item_description(message):
        item_description_new = message.text
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_description', item_description_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Описание товара успешно изменено с\n\n<i>{item_description}</i>\n\nна\n\n'
                                 f'<i>{item_description_new}</i>', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, введите новое описание товара, состоящее не более, чем из 800 символов. '\
               f'Либо отмените операцию'
        await message.answer(text, reply_markup=cancel_markup())


async def change_item_short_description(message: Message, state: FSMContext):
    item_id, item_short_description = await get_data_from_state(state, 'item_id', 'item_short_description')
    if is_requerid_format_item_short_description(message):
        item_short_description_new = message.text if message.text.lower() != 'не требуется' else None
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_short_description', item_short_description_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Описание товара успешно изменено с\n\n<i>{item_short_description}</i>\n\nна\n\n'
                                 f'<i>{item_short_description_new}</i>', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, введите новое короткое описание товара, состоящее не более, чем из 50 символов, ' \
               f'нажмите "Не требуется" либо отмените операцию'
        await message.answer(text, reply_markup=item_short_description_markup())


async def change_item_total_quantity(message: Message, state: FSMContext):
    item_id, item_total_quantity = await get_data_from_state(state, 'item_id', 'item_total_quantity')
    if is_requerid_format_item_total_quantity(message):
        item_total_quantity_new = int(message.text)
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_total_quantity', item_total_quantity_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Количество товара успешно изменено с <b>{item_total_quantity}</b> на '
                                 f'<b>{item_total_quantity_new}</b>', reply_markup=ReplyKeyboardRemove())
    else:
        text = f'🔴 Пожалуйста, пришлите новое количество товара. Количество должно быть от '\
               f'0 до 9999'
        await message.answer(text, reply_markup=cancel_markup())


async def change_item_discontinued(message: Message, state: FSMContext):
    item_id, item_discontinued = await get_data_from_state(state, 'item_id', 'item_discontinued')
    if is_requerid_format_item_discontinued(message):
        item_discontinued_new = True if message.text.lower() == 'не видимый' else False
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_discontinued', item_discontinued_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Статус видимости товара изменен с <b>{visibility(item_discontinued)}</b> на '
                                 f'<b>{visibility(item_discontinued_new)}</b>', reply_markup=ReplyKeyboardRemove())
    else:
        text = '🔴 Пожалуйста, введите новый статус видимости товара. Статус должен быть "Видимый" либо "Не видимый"'
        await message.answer(text, reply_markup=item_discontinued_status_markup())


@album_latency(latency=1)
async def change_item_photo_url_group(message: Message):
    await message.answer('🔴 Пожалуйста, пришлите одно новое фото товара, которое будет установлено для '
                         'быстрого просмотра и выствления счетов. Либо пришлите ссылку на фотографию '
                         'на вашем сайте в формате .jpg или .jpeg, начинающуюся на "http://" или "https://" '
                         'и заканчивающуюся на ".jpeg" или ".jpg". Либо отмените операцию',
                         reply_markup=cancel_markup())


async def change_item_photo_url(message: Message, state: FSMContext, file_uploader: TelegraphService):
    item_id, item_photo_url = await get_data_from_state(state, 'item_id', 'item_photo_url')
    if is_requerid_format_item_photo(message):
        await message.bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_PHOTO)
        err_text = "Проблема на стороне Telegraph. В данный момент нельзя загрузить фото. "\
                   "Вы можете добавить существующую ссылку на фото, если она у вас есть. " \
                   'В противном случае нажмите "Отмена"'
        # item_photo_url_new = await get_photo_link(message)
        uploaded_photo = await on_process_upload_photo(message, logger, state, err_text, file_uploader, cancel_markup())
        if uploaded_photo:
            item_photo_url_new = uploaded_photo.link
            db = get_db(message)
            updated_item = await db.update_item_from_items(item_id, 'item_photo_url', item_photo_url_new)
            if await product_still_exists(message, state, updated_item, item_id):
                await state.finish()
                await message.answer(f'🟢 Новое фото успешно загружено. Новая ссылка сгенерирована. Ссылка на фото '
                                     f'для быстрого просмотра и выставления счетов изменена с:\n\n'
                                     f'{item_photo_url}\n\nна:\n\n{item_photo_url_new}',
                                     reply_markup=ReplyKeyboardRemove())
    elif is_requerid_format_item_photo_url(message):
        item_photo_url_new = message.text
        db = get_db(message)
        updated_item = await db.update_item_from_items(item_id, 'item_photo_url', item_photo_url_new)
        if await product_still_exists(message, state, updated_item, item_id):
            await state.finish()
            await message.answer(f'🟢 Ссылка на фото для быстрого просмотра и выставления счетов изменена с:\n\n'
                                 f'{item_photo_url}\n\nна:\n\n{item_photo_url_new}', reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer('🔴 Пожалуйста, пришлите одно новое фото товара, которое будет установлено для '
                             'быстрого просмотра и выствления счетов. Либо пришлите ссылку на фотографию '
                             'на вашем сайте в формате .jpg или .jpeg, начинающуюся на "http://" или "https://" '
                             'и заканчивающуюся на ".jpeg" или ".jpg". Либо отмените операцию',
                             reply_markup=cancel_markup())


async def delete_item(message: Message, state: FSMContext):
    item_id, item_name = await get_data_from_state(state, 'item_id', 'item_name')
    if is_requerid_format_yes_or_no_markup(message):
        confirmation = True if message.text.lower() == 'да' else False
        if confirmation:
            db = get_db(message)
            try:
                await db.del_item_from_items(item_id)
            except ForeignKeyViolationError:
                await state.finish()
                await message.answer('🔴 Данный товар нельзя удалить по причине того, что он находится у кого-то в '
                                     'корзине. Вы можете отключить видимость товара либо поставить его количество '
                                     'равное 0, чтобы его нельзя было купить. В течение 24 часов товар автоматически '
                                     'удалится из корзины и его можно будет удалить',
                                     reply_markup=ReplyKeyboardRemove())
                await state.finish()
            else:
                await state.finish()
                await message.answer(f'🟢 Товар <b>{item_name}</b> с ID <b>{item_id}</b> успешно удален',
                                     reply_markup=ReplyKeyboardRemove())
        else:
            await state.finish()
            await message.answer(f'🟢 Вы отменили удаление товара <b>{item_name}</b> с ID <b>{item_id}</b>',
                                 reply_markup=ReplyKeyboardRemove())
    else:
        text = '🔴 Пожалуйста, введите "Да", "Нет" либо "Отмена"'
        await message.answer(text, reply_markup=yes_no_reply_markup())


def register_admin_change_item(dp: Dispatcher):
    dp.register_message_handler(change_choose_item_category, state=ChangeItem.item_category_name, **admin_filters)
    dp.register_message_handler(change_choose_item_subcategory, state=ChangeItem.item_subcategory_name,
                                **admin_filters)
    dp.register_message_handler(change_choose_item_name, state=ChangeItem.item_name_choose, **admin_filters)
    dp.register_callback_query_handler(start_changing_item_with_item_id, change_item_cd.filter(), state="*")
    dp.register_message_handler(change_item_id, state=ChangeItem.item_id, **admin_filters)
    dp.register_message_handler(change_item_name, state=ChangeItem.item_name_set, **admin_filters)
    dp.register_message_handler(change_item_photos, is_media_group=True, state=ChangeItem.item_photos, **admin_filters)
    dp.register_message_handler(change_item_photo, state=ChangeItem.item_photos, **admin_filters)
    dp.register_message_handler(change_item_main_photo_group, is_media_group=True, state=ChangeItem.item_main_photo,
                                **admin_filters)
    dp.register_message_handler(change_item_main_photo, state=ChangeItem.item_main_photo, **admin_filters)
    dp.register_message_handler(change_item_price, state=ChangeItem.item_price, **admin_filters)
    dp.register_message_handler(change_item_description, state=ChangeItem.item_description, **admin_filters)
    dp.register_message_handler(change_item_short_description, state=ChangeItem.item_short_description, **admin_filters)
    dp.register_message_handler(change_item_total_quantity, state=ChangeItem.item_total_quantity, **admin_filters)
    dp.register_message_handler(change_item_discontinued, state=ChangeItem.item_discontinued, **admin_filters)
    dp.register_message_handler(change_item_photo_url_group, is_media_group=True, state=ChangeItem.item_photo_url,
                                **admin_filters)
    dp.register_message_handler(change_item_photo_url, state=ChangeItem.item_photo_url, **admin_filters)
    dp.register_message_handler(delete_item, state=ChangeItem.item_delete, **admin_filters)
