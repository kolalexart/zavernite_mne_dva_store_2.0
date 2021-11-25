from aiogram import Dispatcher
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, \
    InlineKeyboardButton, CallbackQuery, Message
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.deep_linking import get_start_link

from tgbot.handlers.user import select_or_add_user_from_or_to_database
from tgbot.keyboards.menu_keyboards.users_keyboards.menu_inline import item_keyboard, make_callback_data
from tgbot.misc.secondary_functions import get_db, get_item_data
from tgbot.misc.texts import UserTexts

show_item_from_inline_cd = CallbackData('show_from_inline', 'item_id', 'telegram_id')


async def prepare_inline_query_answer(query: InlineQuery):
    db = get_db(query)
    telegram_id = query.from_user.id
    name_starts_with = str(query.query)
    items = await db.select_items_like(name_starts_with)
    results = []
    for item in items:
        item = get_item_data(item)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f'Посмотреть в каталоге "{item.item_name}"',
                                     callback_data=show_item_from_inline_cd.new(item_id=item.item_id,
                                                                                telegram_id=telegram_id))
            ]
        ])
        description = item.item_short_description if item.item_short_description else item.item_description
        description = f'Цена: {item.item_price} руб.\n' + description
        result = InlineQueryResultArticle(
            id=str(item.item_id),
            title=item.item_name,
            reply_markup=markup,
            description=description,
            thumb_url=item.item_photo_url,
            input_message_content=InputTextMessageContent(
                message_text=f'Цена: {item.item_price}\n' + item.item_description
            ))
        results.append(result)
    return results


async def show_all_goods(query: InlineQuery):
    if query.chat_type == 'sender':
        query_offset = int(query.offset) if query.offset else 0
        results = await prepare_inline_query_answer(query)
        len_results = len(results)
        if len_results <= 50:
            await query.answer(results=results[query_offset:50], cache_time=5, next_offset='')
        else:
            await query.answer(results=results[query_offset:(query_offset+50)], cache_time=5,
                               next_offset=str(query_offset+50))
    else:
        deep_link = await get_start_link(payload=str(query.from_user.id), encode=True)
        message_text = f'Чтобы начать покупки, переходи по ссылке {deep_link} и жми внизу экрана "СТАРТ" либо "НАЧАТЬ"'
        title = f'☝☝☝ жми кнопку'
        description = 'Или нажми сюда, чтобы отправить ссылку на магазин'
        await query.answer(results=[InlineQueryResultArticle(id='Подключение',
                                                             title=title,
                                                             input_message_content=(
                                                                 InputTextMessageContent(message_text=message_text)),
                                                             description=description)],
                           switch_pm_text='Перейти в магазин',
                           switch_pm_parameter='from_outside',
                           cache_time=5)


async def show_from_inline(call: CallbackQuery, callback_data: dict):
    await call.answer(cache_time=10)
    item_id = int(callback_data.get('item_id'))
    telegram_id = int(callback_data.get('telegram_id'))
    db = get_db(call)
    item_record = await db.get_item_from_items(item_id)
    item = get_item_data(item_record)
    markup = await item_keyboard(call, item, quantity=1)
    message = await call.bot.send_message(text='Вы перемещены в каталог', chat_id=telegram_id)
    await message.answer_photo(photo=item.item_photos[0], caption=UserTexts.item_text(item), reply_markup=markup)


async def start_with_item_name(message: Message):
    user, new_user, referer = await select_or_add_user_from_or_to_database(message)

    markup = InlineKeyboardMarkup()

    markup.row(InlineKeyboardButton(text='Быстрый просмотр всех товаров',
                                    switch_inline_query_current_chat=''))
    markup.row(InlineKeyboardButton(text='Перейти в каталог',
                                    callback_data=make_callback_data('0')))
    if new_user:
        text = f'{user.full_name}, привет! Вы перешли в магазин подарков "Заверните мне два" и ' \
               f'только что были зарегистрированы. Что хотите сделать?'
    else:
        text = f'{user.full_name}, привет! Вы перешли в магазин подарков "Заверните мне два". ' \
               f'Что хотите сделать?'
    await message.answer(text=text, reply_markup=markup)


def register_inline_mode(dp: Dispatcher):
    dp.register_inline_handler(show_all_goods)
    dp.register_callback_query_handler(show_from_inline, show_item_from_inline_cd.filter())
    dp.register_message_handler(start_with_item_name, CommandStart(deep_link='from_outside'))
