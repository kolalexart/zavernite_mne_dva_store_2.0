import typing

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup

from tgbot.handlers.admins.admins_secondary import is_requerid_format_item_category, admin_filters, \
    get_data_from_state, is_requerid_format_yes_or_no_markup, is_requerid_format_item_category_while_renaiming, \
    get_name_and_code, get_items_subcategories, check_on_without_subcategory
from tgbot.keyboards.menu_keyboards.admins_keybords.admins_menu import yes_no_reply_markup, \
    choose_item_category_name_markup, cancel_markup, choose_item_subcategory_name_markup
from tgbot.misc.secondary_functions import get_db, ItemPatterns
from tgbot.misc.states import DeleteItemCategory, ChangeItemCategoryName, ChangeItemSubCategoryName, \
    DeleteItemSubCategory


async def create_success_message(state: FSMContext, item_category_name: str,
                                 item_subcategory_name: typing.Optional[str] = None):
    state = await state.get_state()
    if not item_subcategory_name:
        if state == DeleteItemCategory.item_category_name.state:
            success_message = f'❗❗❗ Вы выбрали категорию товаров <b>"{item_category_name}"</b>. Будет удалена ' \
                              f'категория товаров и все товары, находящиеся в ней. Это действие необратимо. ' \
                              f'Вы уверены, что хотите удалить все товары из категории <b>"{item_category_name}"</b>?'
            return success_message
        elif state == ChangeItemCategoryName.item_category_name.state:
            success_message = f'Вы выбрали категорию товаров <b>"{item_category_name}"</b>. Введите новое название ' \
                              f'категории товаров. Либо отмените операцию:'
            return success_message
        elif state == DeleteItemSubCategory.item_category_name.state:
            success_message = f'Вы выбрали категорию товаров <b>"{item_category_name}"</b>. Выберите подкатегорию, ' \
                              f'которую хотите удалить. Либо отмените операцию:'
            return success_message
        elif state == ChangeItemSubCategoryName.item_category_name.state:
            success_message = f'Вы выбрали категорию товаров <b>"{item_category_name}"</b>. Выберите подкатегорию, ' \
                              f'у которой вы хотите изменить название. Либо отмените операцию:'
            return success_message
    else:
        if state == DeleteItemSubCategory.item_subcategory_name.state:
            success_message = f'❗❗❗ Вы выбрали подкатегорию товаров <b>"{item_subcategory_name}"</b> в категории ' \
                              f'<b>"{item_category_name}"</b>. Будет удалена ' \
                              f'подкатегория товаров и все товары, находящиеся в ней. Это действие необратимо. ' \
                              f'Вы уверены, что хотите удалить все товары из подкатегории ' \
                              f'<b>"{item_subcategory_name}"</b> категории <b>"{item_category_name}"</b>?'
            return success_message
        elif state == ChangeItemSubCategoryName.item_subcategory_name.state:
            success_message = f'Вы выбрали подкатегорию товаров <b>"{item_subcategory_name}"</b> ' \
                              f'в категории <b>"{item_category_name}"</b>. Введите новое ' \
                              f'название подкатегории товаров. Либо отмените операцию:'
            return success_message


async def choose_item_category_name(message: Message, state: FSMContext, success_states_group,
                                    markup: typing.Optional[ReplyKeyboardMarkup] = None, for_subcategory: bool = False):

    list_categories = (await get_data_from_state(state, 'list_categories'))[0]
    if is_requerid_format_item_category(message, list_categories):
        item_category_name, item_category_code = get_name_and_code(message, list_categories)

        if for_subcategory:
            list_subcategories = await get_items_subcategories(message, item_category_code)
            if list_subcategories and check_on_without_subcategory(list_subcategories):
                await message.answer(f'В категории <b>"{item_category_name}"</b> нет подкатегорий. Вы можете '
                                     f'удалить или изменить всю категорию через соответствующий пункт меню '
                                     f'администраторов /admins_menu', reply_markup=ReplyKeyboardRemove())
                await state.finish()
            else:
                success_message = await create_success_message(state, item_category_name)
                markup = choose_item_subcategory_name_markup(list_subcategories)
                await state.update_data(item_category_name=item_category_name,
                                        item_category_code=item_category_code,
                                        list_subcategories=list_subcategories)
                await message.answer(success_message, reply_markup=markup)
                await success_states_group.next()

        else:
            success_message = await create_success_message(state, item_category_name)
            await state.update_data(item_category_name=item_category_name,
                                    item_category_code=item_category_code)
            await message.answer(success_message, reply_markup=markup)
            await success_states_group.next()
    else:
        list_categories = (await get_data_from_state(state, 'list_categories'))[0]
        await message.answer('🔴 Такой категории товаров не существует. Пожалуйста, выберите категорию из предложенных '
                             'ниже либо отмените операцию:',
                             reply_markup=choose_item_category_name_markup(list_categories))


async def choose_item_category_name_for_deleting(message: Message, state: FSMContext):
    await choose_item_category_name(message, state, DeleteItemCategory, yes_no_reply_markup())
    # if await is_requerid_format_item_category(message, state):
    #     item_category_name = message.text.capitalize()
    #     await state.update_data(item_category_name=item_category_name)
    #     await message.answer(f'❗❗❗ Вы выбрали категорию товаров <b>{item_category_name}</b>. Будет удалена категория '
    #                          f'товаров и все товары, находящиеся в ней. Это действие необратимо. Вы уверены, что '
    #                          f'хотите удалить все товары из категории <b>{item_category_name}</b>?',
    #                          reply_markup=yes_no_reply_markup())
    #     await DeleteItemCategory.next()
    # else:
    #     list_categories = (await get_data_from_state(state, 'list_categories'))[0]
    #     await message.answer('🔴 Такой категории товаров не существует. Пожалуйста, выберите категорию из предложенных '
    #                          'ниже либо отмените операцию:',
    #                          reply_markup=choose_item_category_name_markup(list_categories))


async def confirm_deleting_item_category(message: Message, state: FSMContext):
    if is_requerid_format_yes_or_no_markup(message):
        db = get_db(message)
        item_category_name = (await get_data_from_state(state, 'item_category_name'))[0]
        confirmation = message.text.lower()
        if confirmation == 'да':
            quantity_deleted_items = await db.delete_items_from_items(item_category_name=item_category_name)
            await message.answer(f'🟢 Категория товаров <b>"{item_category_name}"</b> и все товары из нее '
                                 f'успешно удалены\nКоличество удаленных товаров в категории '
                                 f'<b>"{item_category_name}"</b>: {quantity_deleted_items}',
                                 reply_markup=ReplyKeyboardRemove())
            await state.finish()
        if confirmation == 'нет':
            await message.answer(f'🟢 Удалении категории товаров <b>"{item_category_name}"</b> успешно отменено ',
                                 reply_markup=ReplyKeyboardRemove())
            await state.finish()
    else:
        text = '🔴 Пожалуйста, введите "Да", "Нет" либо "Отмена"'
        await message.answer(text, reply_markup=yes_no_reply_markup())


async def choose_item_category_name_for_renaiming(message: Message, state: FSMContext):
    await choose_item_category_name(message, state, ChangeItemCategoryName, cancel_markup())


async def set_new_item_category_name(message: Message, state: FSMContext):
    list_categories, item_category_name = await get_data_from_state(state, 'list_categories', 'item_category_name')
    if await is_requerid_format_item_category_while_renaiming(message, list_categories,
                                                              ItemPatterns.ITEM_CATEGORY_NAME):
        db = get_db(message)
        new_item_category_name = message.text
        quantity_updated_items = await db.update_items_from_items('item_category_name', new_item_category_name,
                                                                  item_category_name=item_category_name)
        await message.answer(f'🟢 Название категории товаров <b>"{item_category_name}"</b> успешно изменено на '
                             f'<b>"{new_item_category_name}"</b>\nКоличество товаров с измененной категорией: '
                             f'{quantity_updated_items}', reply_markup=ReplyKeyboardRemove())
        await state.finish()
    else:
        text = f'🔴 Пожалуйста, введите новое название категории товаров, состоящее из не более, чем 30-ти ' \
               f'символов, и отличное от уже имеющихся либо отмените операцию:'
        await message.answer(text, reply_markup=cancel_markup())


async def choose_item_category_name_for_deleting_subcategory(message: Message, state: FSMContext):
    await choose_item_category_name(message, state, DeleteItemSubCategory, for_subcategory=True)


async def choose_item_subcategory_name(message: Message, state: FSMContext, success_states_group,
                                       markup):
    item_category_name, item_category_code, list_subcategories = \
        await get_data_from_state(state, 'item_category_name', 'item_category_code', 'list_subcategories')
    if is_requerid_format_item_category(message, list_subcategories):
        item_subcategory_name, item_subcategory_code = get_name_and_code(message, list_subcategories)
        success_message = await create_success_message(state, item_category_name, item_subcategory_name)
        await state.update_data(item_subcategory_name=item_subcategory_name,
                                item_subcategory_code=item_subcategory_code)
        await message.answer(success_message, reply_markup=markup)
        await success_states_group.next()
    else:
        await message.answer('🔴 Такой подкатегории товаров не существует. Пожалуйста, выберите подкатегорию из '
                             'предложенных ниже либо отмените операцию:',
                             reply_markup=choose_item_subcategory_name_markup(list_subcategories))


async def choose_item_subcategory_name_for_deleting_subcategory(message: Message, state: FSMContext):
    await choose_item_subcategory_name(message, state, DeleteItemSubCategory, yes_no_reply_markup())
    # item_category_name, item_category_code, list_subcategories = \
    #     await get_data_from_state(state, 'item_category_name', 'item_category_code', 'list_subcategories')
    # if is_requerid_format_item_category(message, list_subcategories):
    #     item_subcategory_name, item_subcategory_code = get_name_and_code(message, list_subcategories)
    #     success_message = await create_success_message(state, item_category_name, item_subcategory_name)
    #     await state.update_data(item_subcategory_name=item_subcategory_name,
    #                             item_subcategory_code=item_subcategory_code)
    #     await message.answer(success_message, reply_markup=yes_no_reply_markup())
    #     await DeleteItemSubCategory.next()
    # else:
    #     await message.answer('🔴 Такой подкатегории товаров не существует. Пожалуйста, выберите подкатегорию из '
    #                          'предложенных ниже либо отмените операцию:',
    #                          reply_markup=choose_item_subcategory_name_markup(list_subcategories))


async def confirm_deleting_item_subcategory(message: Message, state: FSMContext):
    if is_requerid_format_yes_or_no_markup(message):
        db = get_db(message)
        item_subcategory_name, item_category_name = await get_data_from_state(state, 'item_subcategory_name',
                                                                              'item_category_name')
        confirmation = message.text.lower()
        if confirmation == 'да':
            quantity_deleted_items = await db.delete_items_from_items(item_category_name=item_category_name,
                                                                      item_subcategory_name=item_subcategory_name)
            await message.answer(f'🟢 Подкатегория товаров <b>"{item_subcategory_name}"</b> в категории '
                                 f'<b>"{item_category_name}"</b> и все товары из нее '
                                 f'успешно удалены.\nКоличество удаленных товаров в категории '
                                 f'<b>"{item_category_name}"</b> в подкатегории <b>"{item_category_name}"</b>: '
                                 f'{quantity_deleted_items}', reply_markup=ReplyKeyboardRemove())
            await state.finish()
        if confirmation == 'нет':
            await message.answer(f'🟢 Удалении подкатегории товаров <b>"{item_subcategory_name}"</b> в '
                                 f'категории <b>"{item_category_name}"</b> успешно отменено ',
                                 reply_markup=ReplyKeyboardRemove())
            await state.finish()
    else:
        text = '🔴 Пожалуйста, введите "Да", "Нет" либо "Отмена"'
        await message.answer(text, reply_markup=yes_no_reply_markup())


async def choose_item_category_name_for_renaiming_subcategory(message: Message, state: FSMContext):
    await choose_item_category_name(message, state, ChangeItemSubCategoryName, for_subcategory=True)


async def choose_item_subcategory_name_for_renaiming_subcategory(message: Message, state: FSMContext):
    await choose_item_subcategory_name(message, state, ChangeItemSubCategoryName, cancel_markup())


async def set_new_item_subcategory_name(message: Message, state: FSMContext):
    list_subcategories, item_subcategory_name, item_category_name = \
        await get_data_from_state(state, 'list_subcategories', 'item_subcategory_name', 'item_category_name')
    if await is_requerid_format_item_category_while_renaiming(message, list_subcategories,
                                                              ItemPatterns.ITEM_SUBCATEGORY_NAME):
        db = get_db(message)
        new_item_subcategory_name = message.text
        quantity_updated_items = await db.update_items_from_items('item_subcategory_name', new_item_subcategory_name,
                                                                  item_category_name=item_category_name,
                                                                  item_subcategory_name=item_subcategory_name)
        await message.answer(f'🟢 Название подкатегории товаров <b>"{item_subcategory_name}"</b> в категори '
                             f'<b>"{item_category_name}"</b> успешно изменено на '
                             f'<b>"{new_item_subcategory_name}"</b>\n'
                             f'Количество товаров с измененной подкатегорией: {quantity_updated_items}',
                             reply_markup=ReplyKeyboardRemove())
        await state.finish()
    else:
        text = f'🔴 Пожалуйста, введите новое название подкатегории товаров, состоящее из не более, чем 30-ти ' \
               f'символов, и отличное от уже имеющихся либо отмените операцию:'
        await message.answer(text, reply_markup=cancel_markup())


def register_admin_change_or_delete_item_category(dp: Dispatcher):
    dp.register_message_handler(choose_item_category_name_for_deleting, state=DeleteItemCategory.item_category_name,
                                **admin_filters)
    dp.register_message_handler(confirm_deleting_item_category, state=DeleteItemCategory.confirm,
                                **admin_filters)
    dp.register_message_handler(choose_item_category_name_for_renaiming,
                                state=ChangeItemCategoryName.item_category_name, **admin_filters)
    dp.register_message_handler(set_new_item_category_name, state=ChangeItemCategoryName.new_item_category_name,
                                **admin_filters)
    dp.register_message_handler(choose_item_category_name_for_deleting_subcategory,
                                state=DeleteItemSubCategory.item_category_name, **admin_filters)
    dp.register_message_handler(choose_item_subcategory_name_for_deleting_subcategory,
                                state=DeleteItemSubCategory.item_subcategory_name, **admin_filters)
    dp.register_message_handler(confirm_deleting_item_subcategory,
                                state=DeleteItemSubCategory.confirm, **admin_filters)
    dp.register_message_handler(choose_item_category_name_for_renaiming_subcategory,
                                state=ChangeItemSubCategoryName.item_category_name, **admin_filters)
    dp.register_message_handler(choose_item_subcategory_name_for_renaiming_subcategory,
                                state=ChangeItemSubCategoryName.item_subcategory_name, **admin_filters)
    dp.register_message_handler(set_new_item_subcategory_name,
                                state=ChangeItemSubCategoryName.new_item_subcategory_name, **admin_filters)
