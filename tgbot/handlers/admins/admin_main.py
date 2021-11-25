from asyncio import sleep

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, ChatTypeFilter, Text
from aiogram.types import Message, ReplyKeyboardRemove, ContentType

from tgbot.handlers.admins.admins_secondary import reject_content_type, admin_filters, get_items_categories
from tgbot.handlers.user import user_start
from tgbot.keyboards.menu_keyboards.admins_keybords.admins_menu import admins_menu_markup, ADMINS_MENU_OPTIONS, \
    choose_item_id_markup, choose_item_category_name_markup
from tgbot.misc.secondary_functions import get_db
from tgbot.misc.states import AdminActions, AddItem, ChangeItem, DeleteItemCategory, ChangeItemCategoryName, \
    ChangeItemSubCategoryName, DeleteItemSubCategory


async def cancel_current_action(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Вы отменили текущее действие. Выберите команду через "меню", что хотите сделать',
                         reply_markup=ReplyKeyboardRemove())


async def exit_from_all_states(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Вы вышли из всех состояний', reply_markup=ReplyKeyboardRemove())


async def admin_start(message: Message, state: FSMContext):
    await user_start(message, state)
    message = await message.reply('Администратор опознан')
    await sleep(2)
    await message.delete()


async def get_photo_id(message: Message, state: FSMContext):
    await state.finish()
    message_with_photo = message.reply_to_message
    photo_id = message_with_photo.photo[-1].file_id
    await message_with_photo.reply(photo_id, reply_markup=ReplyKeyboardRemove())


async def show_admins_menu(message: Message, state: FSMContext):
    await state.finish()
    await message.answer(f'Для вас доступно меню администраторов.\n'
                         f'Вы можете:',
                         reply_markup=admins_menu_markup())
    await AdminActions.add_or_change.set()


async def start_adding_item(message: Message, state: FSMContext):
    db = get_db(message)
    list_items_ids = [item_id_record.get('item_id') for item_id_record in await db.get_items_ids_from_items()]
    list_items_ids_str = [str(item_id_record.get('item_id')) for item_id_record in
                          await db.get_items_ids_from_items()]
    if list_items_ids:
        text = f'Вы выбрали <b>Добавить товар</b>.\n\n'\
               f'<b>ШАГ_1:</b> Введите ID нового товара, либо оставьте значение по умолчанию. '\
               f"Сейчас используются следующие значения ID: {', '.join(list_items_ids_str)}"
    else:
        text = f'Вы выбрали <b>Добавить товар</b>.\n\n'\
               f'<b>ШАГ_1:</b> Введите ID нового товара, либо оставьте значение по умолчанию:'
    await message.answer(text, reply_markup=choose_item_id_markup())
    await state.update_data(list_items_ids=list_items_ids)
    await AddItem.first()


async def start_changing(message: Message, state: FSMContext, success_message: str, success_states_group):
    list_categories = await get_items_categories(message)
    markup = choose_item_category_name_markup(list_categories)
    if list_categories:
        await message.answer(success_message, reply_markup=markup)
        await state.update_data(list_categories=list_categories)
        await success_states_group.first()
    else:
        error_message = 'Ни одного товара еще не создано. Нажмите "Отмена", чтобы продолжить'
        await message.answer(error_message, reply_markup=markup)


async def start_changing_item(message: Message, state: FSMContext):
    success_message = f'Вы выбрали <b>{message.text.capitalize()}</b>.\n\n' \
                      f'Выберите категорию, в которой вы хотите изменить товар:'
    await start_changing(message, state, success_message, ChangeItem)


async def start_deleting_item_category(message: Message, state: FSMContext):
    success_message = f'Вы выбрали <b>{message.text.capitalize()}</b>.\n\n' \
                      f'Выберите категорию, которую вы хотите удалить:'
    await start_changing(message, state, success_message, DeleteItemCategory)


async def start_changing_item_category_name(message: Message, state: FSMContext):
    success_message = f'Вы выбрали <b>{message.text.capitalize()}</b>.\n\n' \
                      f'Выберите категорию, у которой вы хотите изменить название:'
    await start_changing(message, state, success_message, ChangeItemCategoryName)


async def start_deleting_item_subcategory(message: Message, state: FSMContext):
    success_message = f'Вы выбрали <b>{message.text.capitalize()}</b>.\n\n' \
                      f'Выберите категорию, в которой вы хотите удалить подкатегорию:'
    await start_changing(message, state, success_message, DeleteItemSubCategory)


async def start_changing_item_subcategory_name(message: Message, state: FSMContext):
    success_message = f'Вы выбрали <b>{message.text.capitalize()}</b>.\n\n' \
                      f'Выберите категорию, в которой вы хотите изменить название подкатегории:'
    await start_changing(message, state, success_message, ChangeItemSubCategoryName)


async def choose_admin_action(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        if message.text.lower() == ADMINS_MENU_OPTIONS[0].lower():
            await start_adding_item(message, state)
        elif message.text.lower() == ADMINS_MENU_OPTIONS[1].lower():
            await start_changing_item(message, state)
        elif message.text.lower() == ADMINS_MENU_OPTIONS[2].lower():
            await start_deleting_item_category(message, state)
        elif message.text.lower() == ADMINS_MENU_OPTIONS[3].lower():
            await start_changing_item_category_name(message, state)
        elif message.text.lower() == ADMINS_MENU_OPTIONS[4].lower():
            await start_deleting_item_subcategory(message, state)
        elif message.text.lower() == ADMINS_MENU_OPTIONS[5].lower():
            await start_changing_item_subcategory_name(message, state)
        else:
            await message.answer('Такой команды нет. Отправьте команду, нажав на одну из кнопок ниже, введите команду '
                                 'вручную либо отмените операцию', reply_markup=admins_menu_markup())
    else:
        additional_text = f'Отправьте команду, нажав на одну из кнопок ниже, введите команду вручную либо отмените ' \
                          f'операцию'
        await reject_content_type(message, additional_text, admins_menu_markup())


def register_admin_main(dp: Dispatcher):
    dp.register_message_handler(exit_from_all_states, Command('exit'), state="*", is_admin=True)
    dp.register_message_handler(admin_start, Command('start'), state="*", is_admin=True)
    dp.register_message_handler(get_photo_id, ChatTypeFilter(types.ChatType.PRIVATE), Command('get_photo_id'),
                                is_admin=True, is_reply=True)
    dp.register_message_handler(cancel_current_action, Text(equals='отмена', ignore_case=True),
                                state=[AdminActions, AddItem, ChangeItem, DeleteItemCategory, ChangeItemCategoryName,
                                       DeleteItemSubCategory, ChangeItemSubCategoryName],
                                is_admin=True)
    dp.register_message_handler(show_admins_menu, Command('admins_menu'), state='*', is_admin=True)
    dp.register_message_handler(choose_admin_action, state=AdminActions, **admin_filters)
