import logging
import typing

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, ContentType
from asyncpg import UniqueViolationError

from tgbot.handlers.admins.admins_secondary import reject_content_type, get_items_categories, \
    get_items_subcategories, get_data_from_state, admin_filters, get_chosen_category_code, \
    check_on_without_subcategory, full_gproduct_description, choose_category_code_number, \
    choose_subcategory_code_number, ExceededMaxProductSubCategoryQuantity, ExceededMaxProductCategoryQuantity, \
    choose_default_item_id, ExceededMaxProductsQuantity, check_on_items_limits_in_category, \
    check_on_categories_limits, check_on_subcategories_limits, check_on_items_limits_in_subcategory, \
    on_process_upload_photo
from tgbot.keyboards.menu_keyboards.admins_keybords.admins_menu import choose_item_id_markup, \
    choose_item_category_name_markup, choose_item_subcategory_name_markup, \
    cancel_markup, yes_no_reply_markup, item_short_description_markup, admins_menu_markup
from tgbot.middlewares.album import album_latency
from tgbot.misc.secondary_functions import get_db, get_item_data, ItemPatterns
from tgbot.misc.states import AddItem, AdminActions
from tgbot.services.integrations.telegraph.service import TelegraphService

logger = logging.getLogger(__name__)


async def choose_item_id(message: Message, state: FSMContext):
    list_items_ids = (await get_data_from_state(state, 'list_items_ids'))[0]
    items_ids_str = ', '.join(list(map(str, list_items_ids)))
    list_categories = await get_items_categories(message)
    if message.content_type == ContentType.TEXT:
        if list_items_ids:
            error_text = f'🔴 Вы ввели: {message.text}. Пожалуйста, введите целое число в интервале от 1 до 9999 ' \
                         f'отличное от уже использованных: {items_ids_str}. Либо оставьте значение "По умолчанию"'
        else:
            error_text = f'🔴 Вы ввели: {message.text}. Пожалуйста, введите целое число в интервале от 1 до 9999. ' \
                         f'Либо оставьте значение "По умолчанию"'
        pattern = ItemPatterns.ITEM_ID
        if pattern.match(message.text):
            item_id = int(message.text)
            if item_id in list_items_ids:
                await message.answer(error_text, reply_markup=choose_item_id_markup())
            else:
                if list_categories:
                    await message.answer(f'🟢 Ваш ответ ID: <b>{item_id}</b> принят.\n\n'
                                         f'<b>ШАГ_2:</b> Выберите категорию нового товара, либо введите новую:',
                                         reply_markup=choose_item_category_name_markup(list_categories))
                    await state.update_data(item_id=item_id, list_categories=list_categories)
                    await AddItem.next()
                else:
                    await message.answer(f'🟢 Ваш ответ ID: <b>{item_id}</b> принят.\n\n'
                                         f'<b>ШАГ_2:</b> Категорий товара пока не существует. Введите название '
                                         f'новой категории. Либо отмените операцию',
                                         reply_markup=choose_item_category_name_markup(list_categories))
                    await AddItem.next()
        elif message.text.lower() == 'по умолчанию':
            try:
                item_id = choose_default_item_id(list_items_ids)
            except ExceededMaxProductsQuantity as err:
                await message.answer('🔴' + ' ' + err.args[0])
                await state.finish()
            else:
                if list_categories:
                    text = f'🟢 Ваш ответ - оставить ID по умолчанию - принят. Товару присвоен ID '\
                           f'<b>{item_id}</b>\n\n'\
                           f'<b>ШАГ_2:</b> Выберите категорию нового товара, либо введите новую:'
                else:
                    text = f'🟢 Ваш ответ - оставить ID по умолчанию - принят. Товару присвоен ID ' \
                           f'<b>{item_id}</b>\n\n' \
                           f'<b>ШАГ_2:</b> Категорий товара пока не существует. Введите название '\
                           f'новой категории. Либо отмените операцию:'
                await message.answer(text, reply_markup=choose_item_category_name_markup(list_categories))
                await state.update_data(item_id=item_id, list_categories=list_categories)
                await AddItem.next()
        else:
            await message.answer(error_text, reply_markup=choose_item_id_markup())
    else:
        additional_text = f'🔴 Пожалуйста, введите целое число в интервале от 1 до 9999 отличное от ' \
                          f"уже использованных: {items_ids_str}. "
        await reject_content_type(message, additional_text, choose_item_id_markup())


async def choose_item_category_name(message: Message, state: FSMContext):
    list_categories = (await get_data_from_state(state, 'list_categories'))[0]
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_CATEGORY_NAME
        if pattern.match(message.text):
            item_category_name = message.text
            if list_categories:
                list_categories_names = [category[0].lower() for category in list_categories]
                if item_category_name.lower() in list_categories_names:
                    item_category_code = get_chosen_category_code(item_category_name, list_categories)
                    list_subcategories = await get_items_subcategories(message, item_category_code)
                    if list_subcategories and check_on_without_subcategory(list_subcategories):
                        if await check_on_items_limits_in_category(message, item_category_code):
                            await message.answer(f'🟢 Вы выбрали уже существующую категорию: '
                                                 f'<b>{item_category_name}</b>. Код категории: '
                                                 f'<i>{item_category_code}</i>. В этой категории нет '
                                                 f'подкатегорий и уже есть товары. Вам не нужно выбирать подкатегорию, '
                                                 f'поэтому вы сразу перемещаетесь на шаг <b>ШАГ_4</b>.\n\n'
                                                 f'<b>ШАГ_4:</b> Введите название нового товара:',
                                                 reply_markup=cancel_markup())
                            await state.update_data(item_category_name=item_category_name,
                                                    item_category_code=item_category_code)
                            await AddItem.item_name.set()
                        else:
                            await message.answer(f'🔴 В категории <b>{item_category_name}</b> достигнут лимит в 98 '
                                                 f'товаров. В этой категории больше нельзя создать товаров. '
                                                 f'Пожалуйста, создайте новую категорию /admins_menu')
                            await state.finish()
                    else:
                        await message.answer(f'🟢 Вы выбрали уже существующую категорию: <b>{item_category_name}</b>. '
                                             f'Код категории: <i>{item_category_code}</i>. Ваш ответ принят.\n\n'
                                             f'<b>ШАГ_3:</b> Выберите подкатегорию нового товара, либо введите новую:',
                                             reply_markup=choose_item_subcategory_name_markup(list_subcategories))
                        await state.update_data(item_category_name=item_category_name,
                                                item_category_code=item_category_code,
                                                list_subcategories=list_subcategories)
                        await AddItem.next()
                else:
                    if await check_on_categories_limits(message):
                        try:
                            item_category_code = choose_category_code_number(list_categories)
                        except ExceededMaxProductCategoryQuantity as err:
                            await message.answer('🔴' + ' ' + err.args[0], reply_markup=ReplyKeyboardRemove())
                            await state.finish()
                        else:
                            await message.answer(f'🟢 Вы создаете новую категорию: <b>{item_category_name}</b>. '
                                                 f'Новой категории присвоен код {item_category_code}. Ваш ответ '
                                                 f'принят.\n\n'
                                                 f'<b>ШАГ_3:</b> Введите название новой подкатегории товара либо '
                                                 f'выберите "Без подкатегории":',
                                                 reply_markup=choose_item_subcategory_name_markup(
                                                     without_subcategory_btn=True))
                            await state.update_data(item_category_name=item_category_name,
                                                    item_category_code=item_category_code)
                            await AddItem.next()
                    else:
                        await message.answer(f'🔴 Достигнут лимит количества категорий 97. Больше категорий '
                                             f'создать нельзя')
                        await state.finish()
            else:
                item_category_code = choose_category_code_number(list_categories)
                await message.answer(f'🟢 Вы создаете новую категорию: <b>{item_category_name}</b>. '
                                     f'Новой категории присвоен код {item_category_code}. Ваш ответ принят.\n\n'
                                     f'<b>ШАГ_3:</b> Введите название новой подкатегории либо выберите '
                                     f'"Без подкатегории":',
                                     reply_markup=choose_item_subcategory_name_markup(
                                         without_subcategory_btn=True))
                await state.update_data(item_category_name=item_category_name,
                                        item_category_code=item_category_code)
                await AddItem.next()
        else:
            if list_categories:
                text = f'🔴 Вы ввели: {message.text} и в нем {len(message.text)} символов. Пожалуйста, ' \
                       f'введите текст, состоящий из не более, чем 30-ти символов или выберите категорию ' \
                       f'из предложенных ниже:'
                await message.answer(text, reply_markup=choose_item_category_name_markup(list_categories))
            else:
                text = f'🔴 Вы ввели: {message.text} и в нем {len(message.text)} символов. Пожалуйста, ' \
                       f'введите текст, состоящий из не более, чем 30-ти символов:'
                await message.answer(text, reply_markup=choose_item_category_name_markup(list_categories))
    else:
        if list_categories:
            additional_text = f'🔴 Пожалуйста, введите текст, состоящий из не более, ' \
                              f'чем 30-ти символов или выберите категорию из предложенных ниже:'
            await reject_content_type(message, additional_text, choose_item_category_name_markup(list_categories))
        else:
            additional_text = f'🔴 Пожалуйста, введите текст, состоящий из не более, ' \
                              f'чем 30-ти символов:'
            await reject_content_type(message, additional_text, choose_item_category_name_markup())


async def choose_item_subcategory_name(message: Message, state: FSMContext):
    list_subcategories, item_category_code = await get_data_from_state(state, 'list_subcategories',
                                                                       'item_category_code')
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_SUBCATEGORY_NAME
        if pattern.match(message.text):
            item_subcategory_name = message.text
            if list_subcategories:
                item_subcategory_code = get_chosen_category_code(item_subcategory_name, list_subcategories)
                list_subcategories_names = [subcategory[0].lower() for subcategory in list_subcategories]
                if item_subcategory_name.lower() in list_subcategories_names:
                    if await check_on_items_limits_in_subcategory(message, item_category_code, item_subcategory_code):
                        await message.answer(f'🟢 Вы выбрали уже существующую подкатегорию: '
                                             f'<b>{item_subcategory_name}</b>. '
                                             f'Код подкатегории: <i>{item_subcategory_code}</i>. Ваш ответ принят.\n\n'
                                             f'<b>ШАГ_4:</b> Введите название нового товара:',
                                             reply_markup=cancel_markup())
                        await state.update_data(item_subcategory_name=item_subcategory_name,
                                                item_subcategory_code=item_subcategory_code,
                                                list_subcategories=list_subcategories)
                        await AddItem.next()
                    else:
                        await message.answer(f'🔴 Достигнут лимит количества товаров в этой подкатегории - 98. Больше '
                                             f'товаров в эту подкатегорию добавить нельзя. Пожалуйста, создайте '
                                             f'новую подкатегорию /admins_menu')
                        await state.finish()
                else:
                    if item_subcategory_name.lower() == 'без подкатегории':
                        await message.answer(f'🔴 В этой категории уже есть товары с подкатегорией, поэтому нельзя '
                                             f'добавить новый товар без подкатегории. Выберите уже существующую'
                                             f'подкатегорию из представленных ниже либо введите новую:',
                                             reply_markup=choose_item_subcategory_name_markup(list_subcategories))
                    else:
                        if await check_on_subcategories_limits(message, item_category_code):
                            try:
                                item_subcategory_code = choose_subcategory_code_number(list_subcategories,
                                                                                       item_category_code)
                            except ExceededMaxProductSubCategoryQuantity as err:
                                await message.answer('🔴' + ' ' + err.args[0], reply_markup=ReplyKeyboardRemove())
                                await state.finish()
                            else:
                                await message.answer(f'🟢 Вы создаете новую подкатегорию: '
                                                     f'<b>{item_subcategory_name}</b>. '
                                                     f'Новой подкатегории присвоен код {item_subcategory_code}. '
                                                     f'Ваш ответ принят.\n\n'
                                                     f'<b>ШАГ_4:</b> Введите название нового товара:',
                                                     reply_markup=cancel_markup())
                                await state.update_data(item_subcategory_name=item_subcategory_name,
                                                        item_subcategory_code=item_subcategory_code,
                                                        list_subcategories=list_subcategories)
                                await AddItem.next()
                        else:
                            await message.answer(f'🔴 Достигнут лимит количества подкатегорий в этой категории - 98. '
                                                 f'Больше подкатегорий в этой категории создать нельзя')
                            await state.finish()
            else:
                if item_subcategory_name == "Без подкатегории":
                    await message.answer('🟢 Ваш ответ - "Без подкатегории" - принят.\n\n'
                                         '<b>ШАГ_4:</b> Введите название нового товара:',
                                         reply_markup=cancel_markup())
                    await AddItem.next()
                else:
                    item_subcategory_code = choose_subcategory_code_number(list_subcategories, item_category_code)
                    await message.answer(f'🟢 Вы создаете новую подкатегорию: <b>{item_subcategory_name}</b>. '
                                         f'Новой подкатегории присвоен код {item_subcategory_code}. Ваш ответ '
                                         f'принят.\n\n'
                                         f'<b>ШАГ_4:</b> Введите название нового товара:',
                                         reply_markup=cancel_markup())
                    await state.update_data(item_subcategory_name=item_subcategory_name,
                                            item_subcategory_code=item_subcategory_code)
                    await AddItem.next()
        else:
            if list_subcategories:
                text = f'🔴 Вы ввели: {message.text} и в нем {len(message.text)} символов. Пожалуйста, ' \
                       f'введите текст, состоящий из не более, чем 30-ти символов или выберите подкатегорию ' \
                       f'из предложенных ниже:'
                await message.answer(text, reply_markup=choose_item_subcategory_name_markup(list_subcategories))
            else:
                text = f'🔴 Вы ввели: {message.text} и в нем {len(message.text)} символов. Пожалуйста, ' \
                       f'введите текст, состоящий из не более, чем 30-ти символов:'
                await message.answer(text, reply_markup=choose_item_subcategory_name_markup(list_subcategories))
    else:
        if list_subcategories:
            additional_text = f'🔴 Пожалуйста, введите текст, состоящий из не более, ' \
                              f'чем 30-ти символов или выберите категорию из предложенных ниже:'
            await reject_content_type(message, additional_text, choose_item_subcategory_name_markup(list_subcategories))
        else:
            additional_text = f'🔴 Пожалуйста, введите текст, состоящий из не более, ' \
                              f'чем 30-ти символов:'
            await reject_content_type(message, additional_text, choose_item_subcategory_name_markup(list_subcategories))


async def choose_item_name(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_NAME
        if pattern.match(message.text):
            item_name = message.text
            db = get_db(message)
            list_items_names = [item_name_record.get('item_name').lower() for item_name_record in
                                await db.get_items_names_from_items()]
            if item_name.lower() in list_items_names:
                await message.answer(f'🔴 Название товара: <b>{item_name}</b> уже существует. Введите другое название, '
                                     f'отличное от уже имеющихся',
                                     reply_markup=cancel_markup())
            else:
                await state.update_data(item_name=item_name)
                await message.answer(f'🟢 Вы ввели название товара: <b>{item_name}</b>. Ваш ответ принят.\n\n'
                                     f'<b>ШАГ_5:</b> Пришлите фотографии товара. Фотографии должны быть присланы '
                                     f'картинкой или группой фотографий:', reply_markup=cancel_markup())
                await state.update_data(item_name=item_name)
                await AddItem.next()
        else:
            text = f'🔴 Вы ввели: {message.text} и в нем {len(message.text)} символов. Пожалуйста, ' \
                   f'введите текст, состоящий из не более, чем 30-ти символов'
            await message.answer(text, reply_markup=cancel_markup())
    else:
        additional_text = '🔴 Пожалуйста, введите текст, состоящий из не более, чем 30-ти символов'
        await reject_content_type(message, additional_text, cancel_markup())


@album_latency(latency=1)
async def load_photos(message: Message, state: FSMContext, album: typing.List[types.Message]):
    not_a_photo_numbers = list()
    list_photos = list()
    for index, message in enumerate(album, start=1):
        if message.content_type != ContentType.PHOTO:
            not_a_photo_numbers.append(index)
        else:
            list_photos.append(message.photo[-1].file_id)
    if not_a_photo_numbers:
        await message.answer(f'🔴 Порядковые номера отправленных файлов, которые не являются фотографиями:\n'
                             f'{", ".join(map(str, not_a_photo_numbers))}\nПопробуйте еще раз, но только с '
                             f'фотографиями и не более 10 шт.', reply_markup=cancel_markup())
    else:
        await message.answer(f'🟢 Количество загруженных фото: {len(list_photos)}.\nВсе фотографии '
                             f'загружены успешно.\n\n'
                             f'<b>ШАГ_6:</b> Пришлите цену товара в рублях. Цена должна быть без копеек',
                             reply_markup=cancel_markup())
        await state.update_data(item_photos=list_photos)
        await AddItem.next()


async def load_photo(message: Message, state: FSMContext):
    if message.content_type == ContentType.PHOTO:
        photo = message.photo[-1].file_id
        item_photos = [photo]
        await message.answer(f'🟢 Количество загруженных фото: 1. Фотография успешно загружена.\n\n'
                             f'<b>ШАГ_6:</b> Введите цену товара в рублях. Цена должна быть без копеек',
                             reply_markup=cancel_markup())
        await state.update_data(item_photos=item_photos)
        await AddItem.next()
    else:
        additional_text = '🔴 Пожалуйста, пришлите фотографии до 10 шт.'
        await reject_content_type(message, additional_text, cancel_markup())


async def set_item_price(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_PRICE
        if pattern.match(message.text):
            item_price = int(message.text)
            await message.answer(f'🟢 Вы указали стоимость товара: <b>{item_price} руб.</b> '
                                 f'Ваш ответ принят.\n\n'
                                 f'<b>ШАГ_7:</b> Введите описание нового товара (не более 800 символов):',
                                 reply_markup=cancel_markup())
            await state.update_data(item_price=item_price)
            await AddItem.next()
        else:
            await message.answer(f'🔴 Вы ввели цену товара: {message.text}. Пожалуйста, введите число от 10 до 1000000',
                                 reply_markup=cancel_markup())
    else:
        additional_text = '🔴 Пожалуйста, введите число от 10 до 1000000'
        await reject_content_type(message, additional_text, cancel_markup())


async def set_item_description(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_DESCRIPTION
        if pattern.match(message.text):
            item_description = message.text
            await message.answer(f'🟢 Вы указали следующее описание товара:\n<i>{item_description}</i>\n'
                                 f'Ваш ответ принят.\n\n'
                                 f'<b>ШАГ_8:</b> Введите короткое описание товара, если оно требуется:',
                                 reply_markup=item_short_description_markup())
            await state.update_data(item_description=item_description)
            await AddItem.next()
        else:
            await message.answer(f'🔴 В вашем описании товара {len(message.text)} символов. Пожалуйста, уменьшите, '
                                 f'чтобы было не более 800',
                                 reply_markup=cancel_markup())
    else:
        additional_text = '🔴 Пожалуйста, введите текст длиной до 800 символов'
        await reject_content_type(message, additional_text, cancel_markup())


async def set_item_short_description(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_SHORT_DESCRIPTION
        if pattern.match(message.text):
            item_short_description = message.text
            if item_short_description.lower() == 'не требуется':
                await message.answer(f'🟢 Вы указали, что короткое описание товара не требуется. Ваш ответ принят.\n\n'
                                     f'<b>ШАГ_9:</b> Введите количество товара, доступное к покупке:',
                                     reply_markup=cancel_markup())
                await AddItem.next()
            else:
                await message.answer(f'🟢 Вы указали следующее короткое описание товара:\n'
                                     f'<i>{item_short_description}</i>\nВаш ответ принят.\n\n'
                                     f'<b>ШАГ_9:</b> Введите количество товара, доступное к покупке:',
                                     reply_markup=cancel_markup())
                await state.update_data(item_short_description=item_short_description)
                await AddItem.next()
        else:
            await message.answer(f'🔴 В вашем коротком описании товара {len(message.text)} символов. Пожалуйста, '
                                 f'уменьшите, чтобы было не более 50 либо нажмите "Не требуется"',
                                 reply_markup=item_short_description_markup())
    else:
        additional_text = '🔴 Пожалуйста, введите текст длиной до 50 символов либо нажмите "Не требуется"'
        await reject_content_type(message, additional_text, item_short_description_markup())


async def set_item_quantity(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_TOTAL_QUANTITY
        if pattern.match(message.text):
            item_total_quantity = int(message.text)
            await message.answer(f'🟢 Вы указали количество товара: <b>{item_total_quantity}</b> '
                                 f'Ваш ответ принят.\n\n'
                                 f'<b>ШАГ_10:</b> Введите, будет ли товар виден покупателю:',
                                 reply_markup=yes_no_reply_markup())
            await state.update_data(item_total_quantity=item_total_quantity)
            await AddItem.next()
        else:
            await message.answer(f'🔴 Вы указали количество товара: {message.text}. Пожалуйста, введите число от 0 '
                                 f'до 9999',
                                 reply_markup=cancel_markup())
    else:
        additional_text = '🔴 Пожалуйста, введите число от 0 до 9999'
        await reject_content_type(message, additional_text, cancel_markup())


async def choose_item_discontinued(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        if message.text.lower() in ['да', 'нет']:
            if message.text.lower() == 'да':
                item_discontinued = False
                await message.answer('🟢 Вы указали, что товар будет сразу виден покупателю. Ваш ответ принят.\n\n'
                                     '<b>ШАГ_11:</b> Пришлите одно фото, которое будет доступно в быстром просмотре и '
                                     'будет использовано для выставления счетов. Либо пришлите ссылку на фотографию '
                                     'на вашем сайте в формате .jpg или .jpeg, начинающуюся на "http://" или '
                                     '"https://" и заканчивающуюся на ".jpeg" или ".jpg"',
                                     reply_markup=cancel_markup())
                await state.update_data(item_discontinued=item_discontinued)
                await AddItem.next()
            else:
                item_discontinued = True
                await message.answer('🟢 Вы указали, что товар не будет виден покупателю. Ваш ответ принят.\n\n'
                                     '<b>ШАГ_11:</b> Пришлите одно фото, которое будет доступно в быстром просмотре и '
                                     'будет использовано для выставления счетов. Либо пришлите ссылку на фотографию '
                                     'на вашем сайте в формате .jpg или .jpeg, начинающуюся на "http://" или '
                                     '"https://" и заканчивающуюся на ".jpeg" или ".jpg"',
                                     reply_markup=cancel_markup())
                await state.update_data(item_discontinued=item_discontinued)
                await AddItem.next()
        else:
            await message.answer('🔴 Пришлите ответ "Да" либо "Нет" либо воспользуйтесь клавиатурой ниже для ответа:',
                                 reply_markup=yes_no_reply_markup())
    else:
        additional_text = '🔴 Пришлите ответ "Да" либо "Нет" либо воспользуйтесь клавиатурой ниже для ответа:'
        await reject_content_type(message, additional_text, yes_no_reply_markup())


@album_latency(latency=1)
async def refuse_item_photos_for_url(message: Message):
    await message.answer('🔴 Медиа группа не поддерживается. Пожалуйста, пришлите одно фото, которое будет '
                         'доступно в быстром просмотре и будет использовано для выставления счетов. Либо пришлите '
                         'ссылку на фотографию на вашем сайте в формате .jpg или .jpeg, начинающуюся на '
                         '"http://" или "https://" и заканчивающуюся на ".jpeg" или ".jpg"',
                         reply_markup=cancel_markup())


async def set_item_photo_url(message: Message, state: FSMContext, file_uploader: TelegraphService):
    if message.content_type == ContentType.TEXT:
        pattern = ItemPatterns.ITEM_PHOTO_URL
        if pattern.match(message.text.lower()):
            item_photo_url = message.text
            await message.answer(f'🟢 Ссылка на фотографию:\n\n{item_photo_url}\n\nпринята. '
                                 f'Фотография успешно загружена.')
            await state.update_data(item_photo_url=item_photo_url)
            await load_to_database_from_state(message, state)
        else:
            await message.answer(f'🔴 Вы прислали: {message.text}. Пожалуйста, пришлите одно фото, которое будет '
                                 f'доступно в быстром просмотре и будет использовано для выставления счетов. Либо '
                                 f'пришлите ссылку на фотографию на вашем сайте в формате .jpg или .jpeg, '
                                 f'начинающуюся на "http://" или "https://" и заканчивающуюся на ".jpeg" или ".jpg"',
                                 reply_markup=cancel_markup())
    elif message.content_type == ContentType.PHOTO:
        await message.bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_PHOTO)
        err_text = "Проблема на стороне Telegraph. В данный момент нельзя загрузить фото. "\
                   "Вы можете добавить существующую ссылку на фото, если она у вас есть. " \
                   'В противном случае нажмите "Отмена", чтобы повторить добавление товара позднее'
        # item_photo_url = await get_photo_link(message)
        uploaded_photo = await on_process_upload_photo(message, logger, state, err_text, file_uploader, cancel_markup())
        if uploaded_photo:
            item_photo_url = uploaded_photo.link
            await message.answer(f'🟢 Фотография успешно загружена. Ссылка на фото сгенерирована:\n\n'
                                 f'{item_photo_url}')
            await state.update_data(item_photo_url=item_photo_url)
            await load_to_database_from_state(message, state)
    else:
        additional_text = f'🔴 Пожалуйста, пришлите одно фото, которое будет доступно ' \
                          f'в быстром просмотре и будет использовано для выставления счетов. Либо пришлите ' \
                          f'ссылку на фотографию на вашем сайте в формате .jpg или .jpeg, начинающуюся на ' \
                          f'"http://" или "https://" и заканчивающуюся на ".jpeg" или ".jpg"'
        await reject_content_type(message, additional_text, cancel_markup())


async def load_to_database_from_state(message: Message, state: FSMContext):
    state_data_names = ['item_id', 'item_category_name', 'item_category_code', 'item_subcategory_name',
                        'item_subcategory_code', 'item_name', 'item_photos', 'item_price', 'item_description',
                        'item_short_description', 'item_total_quantity', 'item_discontinued', 'item_photo_url']
    state_data = await get_data_from_state(state, *state_data_names)
    db = get_db(message)
    try:
        item_record = await db.load_item_to_items(*state_data)
    except UniqueViolationError as err:
        key, value = parse_unique_violation_error(err.as_dict().get("detail"))
        text = '🔴' + ' ' + text_for_unique_violation_error(key, value)
        await message.answer(text, reply_markup=admins_menu_markup())
        await state.finish()
        await AdminActions.add_or_change.set()
    else:
        item = get_item_data(item_record)
        await state.finish()
        text = '🟢 Следующий товар успешно добавлен в базу данных:\n\n' + full_gproduct_description(item)
        await message.answer(text, reply_markup=ReplyKeyboardRemove())


def parse_unique_violation_error(detail: str) -> typing.Tuple[str, str]:
    key, value = [_.strip('()') for _ in detail.split(' ')[1].strip('"').split('=')]
    return key, value


def text_for_unique_violation_error(key: str, value: str):
    if key == 'item_id':
        item_id = int(value)
        text = f'Товар с <b>"ID {item_id}"</b> уже существует. Создайте новый товар с уникальным значением <b>"ID"</b>'
        return text
    elif key == 'item_name':
        item_name = value
        text = f'Товар с <b>Названием: "{item_name}"</b> уже существует. Создайте новый товар с уникальным названием'
        return text


def register_admin_add_item(dp: Dispatcher):
    dp.register_message_handler(choose_item_id, state=AddItem.item_id, **admin_filters)
    dp.register_message_handler(choose_item_category_name, state=AddItem.item_category_name, **admin_filters)
    dp.register_message_handler(choose_item_subcategory_name, state=AddItem.item_subcategory_name, **admin_filters)
    dp.register_message_handler(choose_item_name, state=AddItem.item_name, **admin_filters)
    dp.register_message_handler(load_photos, is_media_group=True, state=AddItem.item_photos, **admin_filters)
    dp.register_message_handler(load_photo, state=AddItem.item_photos, **admin_filters)
    dp.register_message_handler(set_item_price, state=AddItem.item_price, **admin_filters)
    dp.register_message_handler(set_item_description, state=AddItem.item_description, **admin_filters)
    dp.register_message_handler(set_item_short_description, state=AddItem.item_short_description, **admin_filters)
    dp.register_message_handler(set_item_quantity, state=AddItem.item_total_quantity, **admin_filters)
    dp.register_message_handler(choose_item_discontinued, state=AddItem.item_discontinued, **admin_filters)
    dp.register_message_handler(refuse_item_photos_for_url, is_media_group=True, state=AddItem.item_photo_url,
                                **admin_filters)
    dp.register_message_handler(set_item_photo_url, state=AddItem.item_photo_url, **admin_filters)
