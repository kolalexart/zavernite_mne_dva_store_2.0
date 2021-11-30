import datetime
import logging
import typing

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, LabeledPrice, ShippingQuery, PreCheckoutQuery, ShippingAddress, Message
from apscheduler.jobstores.base import JobLookupError

from tgbot.handlers.payments.telegram_built_in.shipping_options import ShippingOptions
from tgbot.handlers.user import get_item, prepare_markup_for_basket, on_show_basket
from tgbot.keyboards.menu_keyboards.users_keyboards.menu_inline import buy_item, categories_keyboard
from tgbot.misc.schedule import remove_clear_basket_job
from tgbot.misc.secondary_functions import get_db, get_config, get_item_in_basket_data, Item, delete_message
from tgbot.misc.texts import UserTexts

logger = logging.getLogger(__name__)


async def is_item_changed(target: typing.Union[CallbackQuery, Item],
                          item_id: typing.Optional[int], item_quantity: int):
    if not target:
        return None, None, None

    item = target if isinstance(target, Item) else await get_item(target, int(item_id))

    if item.item_discontinued or item.item_total_quantity == 0:
        return item, True, None
    elif item_quantity > item.item_total_quantity:
        new_quantity = item.item_total_quantity
        return item, False, new_quantity
    else:
        return item, False, None


async def check_item(target: typing.Union[CallbackQuery, Item],
                     item_id: typing.Optional[int], item_quantity: int):
    item, item_discontinued, new_quantity = await is_item_changed(target, item_id, item_quantity)
    if not any((item, item_discontinued, new_quantity)):
        return False, (None, None)
    elif item and item_discontinued:
        return False, (None, None)
    elif item and new_quantity:
        return True, (item, new_quantity)
    else:
        return True, (item, None)


async def prepare_data_for_item_invoice(call: CallbackQuery, callback_data: dict) -> typing.Tuple[bool, tuple]:
    prices = []
    item_id = callback_data.get("item_id")
    quantity = callback_data.get('quantity')
    item = await get_item(call, int(item_id))
    ok, (item, new_quantity) = await check_item(item, None, int(quantity))
    if ok and item and new_quantity:
        await call.answer(f'Максимально возможное количество товара: "{item.item_name}", доступное к покупке '
                          f'{new_quantity}', show_alert=True)
        return False, (None, None, None, None, None, None)
    elif ok:
        name = item.item_name
        amount = item.item_price * int(quantity) * 100
        title = (name + ' - ' + quantity + ' шт.')[0:32]
        label = f'{name} - {quantity} шт.'
        payload = f'{item_id}:{quantity}:i'
        price = LabeledPrice(label=label, amount=amount)
        prices.append(price)
        total_price = amount // 100
        description = item.item_short_description if item.item_short_description else item.item_description
        photo_url = item.item_photo_url
        return True, (payload, title, description, prices, photo_url, total_price)
    else:
        if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
            await call.message.answer_photo(UserTexts.PHOTO_LOGO,
                                            UserTexts.user_products_out_of_stock_while_change(item_id),
                                            reply_markup=await categories_keyboard(call))
            return False, (None, None, None, None, None, None)


async def prepare_data_for_basket_invoice(call: CallbackQuery) -> typing.Tuple[bool, tuple]:
    prices = []
    total_price = 0
    payload = str()
    description = f"Счет на ваш заказ:"
    db = get_db(call)
    items_from_basket = await db.select_items_from_basket(call.from_user.id)
    alert_text = str()
    updated_items_in_basket_list = list()
    deleted_items_in_basket_list = list()
    for item in items_from_basket:
        item_in_basket = get_item_in_basket_data(item)
        ok, (item, new_quantity) = await check_item(call, item_in_basket.item_id, item_in_basket.quantity)
        if ok and item and new_quantity:
            alert_text += (f'Максимально возможное количество товара: "{item.item_name}", доступное к покупке '
                           f'{new_quantity}. Количество товара в корзине изменено\n\n')
            updated_item_in_basket_record = await db.change_quantity_item_in_basket(call.from_user.id,
                                                                                    item_in_basket.item_id,
                                                                                    new_quantity,
                                                                                    datetime.datetime.utcnow())
            updated_item_in_basket = get_item_in_basket_data(updated_item_in_basket_record)
            updated_items_in_basket_list.append(updated_item_in_basket)
        elif ok:
            lable = f'"{item_in_basket.item_name}" - {item_in_basket.quantity} шт.'
            amount = item_in_basket.quantity * item_in_basket.item_price * 100
            price = LabeledPrice(label=lable, amount=amount)
            prices.append(price)
            total_price += amount
            payload += f'{item_in_basket.item_id}:{item_in_basket.quantity}:'
        else:
            alert_text += (f'Товар <b>"{item_in_basket.item_name}"</b> с <b>ID {item_in_basket.item_id}</b> больше '
                           f'недоступен. Товар удален из корзины\n')
            await db.delete_item_from_basket(call.from_user.id, item_in_basket.item_id)
            deleted_items_in_basket_list.append(item_in_basket)
    if not updated_items_in_basket_list and not deleted_items_in_basket_list:
        payload += 'b'
        total_price = total_price // 100
        title = "Корзина"
        photo_url = "https://i.pinimg.com/originals/08/be/fb/08befb0acad2f785207804a3b219f103.jpg"
        return True, (payload, title, description, prices, photo_url, total_price)
    if updated_items_in_basket_list or deleted_items_in_basket_list:
        text, basket_list_items = await prepare_markup_for_basket(call)
        if not basket_list_items:
            text = alert_text + '\nВ корзине больше не осталось товаров. Вы перемещены в начало каталога'
        else:
            text = alert_text + "\n" + text
        await on_show_basket(call, text, basket_list_items)
        return False, (None, None, None, None, None, None)


def check_on_total_price(total_price: int) -> bool:
    if total_price <= 1000000:
        return True
    return False


async def send_invoice(call: CallbackQuery, callback_data: dict):
    config = get_config(call)
    provider_token = config.misc.provider_token_sber
    if callback_data.get('item_id') == 'basket':
        ok, (payload, title, description, prices, photo_url, total_price) = await prepare_data_for_basket_invoice(call)
    else:
        ok, (payload, title, description, prices, photo_url, total_price) = \
            await prepare_data_for_item_invoice(call, callback_data)
    if ok:
        if check_on_total_price(total_price):
            await call.answer(cache_time=3)
            # await call.message.delete()
            if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
                await call.bot.send_invoice(chat_id=call.message.chat.id,
                                            provider_token=provider_token,
                                            payload=payload,
                                            title=title,
                                            description=description[0:255],
                                            currency='RUB',
                                            prices=prices,
                                            start_parameter='',
                                            photo_url=photo_url,
                                            photo_size=600,
                                            need_shipping_address=True,
                                            need_name=True,
                                            need_email=True,
                                            need_phone_number=True,
                                            is_flexible=True,
                                            send_email_to_provider=True,
                                            send_phone_number_to_provider=True)
        else:
            await call.answer(cache_time=3)
            # await call.message.delete()
            if await delete_message(call, logger, UserTexts.PHOTO_LOGO, reboot_text=UserTexts.USER_REBOOT_BOT):
                await call.message.answer('Сумма вашей покупки должна быть не более 1000000 руб. Для того, чтобы '
                                          'совершить покупки на большую сумму, вам необходимо разбить заказ на '
                                          'несколько чтобы сумма каждого не превышала 1 млн руб. Пожалуйста, нажмите '
                                          '/menu и перейдите в корзину, если вы совершали покупки через корзину, '
                                          'или просто уменьшите количество покупаемого товара, чтобы сумма не '
                                          'привышала 1 млн руб.')


async def choose_shipping(query: ShippingQuery):
    if query.shipping_address.country_code == "RU":
        await query.bot.answer_shipping_query(shipping_query_id=query.id,
                                              shipping_options=ShippingOptions.all_options(),
                                              ok=True)
    else:
        await query.bot.answer_shipping_query(shipping_query_id=query.id,
                                              ok=False,
                                              error_message='Сюда не доставляем')


async def prepare_data_for_pre_checkout_query(query: PreCheckoutQuery) -> typing.Tuple[bool, str, int]:
    invoice_payload = query.invoice_payload
    list_invoice_payload = invoice_payload.split(':')
    shipping_option_id = query.shipping_option_id
    total_amount_without_shipping = (query.total_amount // 100) - (ShippingOptions.price(shipping_option_id) // 100)
    text = str()
    ok = True
    new_total_amount = 0
    for index_item_id in range(0, len(list_invoice_payload) - 1, 2):
        item_id = int(list_invoice_payload[index_item_id])
        quantity = int(list_invoice_payload[index_item_id + 1])
        item = await get_item(query, item_id)
        if item:
            amount = item.item_price * quantity
            new_total_amount += amount
            if item.item_discontinued:
                text += f'\nК сожалениию, товар "{item.item_name}" c ID {item.item_id} снят с производства\n'
                ok = False
            elif quantity > item.item_total_quantity:
                text += f'\nК сожалению, товар "{item.item_name}" с ID {item.item_id}\n'\
                        f'oсталось {item.item_total_quantity} шт.\n'\
                        f'Вы заказываете {quantity} шт.\n\n'
                ok = False
        else:
            text += f'\nК сожалению, товар с ID {item_id} больше не продается\n'
            ok = False
    if ok and total_amount_without_shipping != new_total_amount:
        text += '\nК сожалению, цена одного из товаров со времени выставления счета изменилась либо каких-то товаров '\
                'нет в наличии. Счет больше недействителен. Пожалуйста, пересоздайте заказ'
        ok = False
    if ok:
        text = 'Данные отправлены. Ждем поступление оплаты'
    return ok, text, new_total_amount


async def process_pre_checkout_query(query: PreCheckoutQuery):
    ok, text, new_total_amount = await prepare_data_for_pre_checkout_query(query)
    if ok:
        await query.bot.answer_pre_checkout_query(pre_checkout_query_id=query.id,
                                                  ok=True)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=text)
    else:
        await query.bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=False,
                                                  error_message=text)


def get_shipping_addres(addres: ShippingAddress) -> str:
    country_code = addres.country_code
    state = addres.state
    city = addres.city
    street = addres.street_line1 + ' ' + addres.street_line2
    post_code = addres.post_code
    return f'{country_code}, {post_code}, {state}, {city}, {street}' if state else \
        f'{country_code}, {post_code}, {city}, {street}'


def get_customer_info(message: Message) -> typing.Tuple[str, str]:
    customer_name = message.successful_payment.order_info.name
    customer_phone_number = message.successful_payment.order_info.phone_number
    customer_email = message.successful_payment.order_info.email
    customer_addres = get_shipping_addres(message.successful_payment.order_info.shipping_address)
    customer_info = f"Поступил заказ от {customer_name}\n"\
                    f"Номер телефона: {customer_phone_number}\n" \
                    f"Электронная почта: {customer_email}\n" \
                    f"Доставка по адресу: {customer_addres}\n\n" \
                    f"Заказ:\n\n"
    return customer_info, customer_email


def order_info_for_admins(item: Item, number: int, quantity: int) -> str:
    order_info = f'{number}. ID {item.item_id} {item.item_name} - {quantity} шт. ' \
                 f'* {item.item_price} руб. = {item.item_price*quantity} руб.\nНа складе осталось: ' \
                 f'{item.item_total_quantity - quantity} шт.\n\n'
    return order_info


async def prepare_data_for_succesfull_payment(message: Message) -> typing.Tuple[str, str]:
    text_for_customer = "Вы оплатили:\n\n"
    text_for_admins = str()
    number = 1
    total_for_goods = 0
    db = get_db(message)
    list_invoice_payload = message.successful_payment.invoice_payload.split(':')
    for index_item_id in range(0, len(list_invoice_payload) - 1, 2):
        item_id = int(list_invoice_payload[index_item_id])
        quantity = int(list_invoice_payload[index_item_id + 1])
        item = await get_item(message, item_id)
        new_quantity = item.item_total_quantity - quantity
        text_for_admins += order_info_for_admins(item, number, quantity)
        await db.update_item_from_items(item_id, 'item_total_quantity', new_quantity)
        text_for_customer += f'{number}. <b>{item.item_name}</b> - {quantity} шт. Сумма: ' \
                             f'{item.item_price*quantity} руб.\n\n'
        number += 1
        total_for_goods += item.item_price*quantity
    text_for_customer += f'<b>Итого за товары:</b> {total_for_goods} руб.'
    text_for_admins += f'<b>Итого за товары:</b> {total_for_goods} руб.'
    return text_for_customer, text_for_admins


def is_order_from_basket(message: Message) -> bool:
    list_invoice_payload = message.successful_payment.invoice_payload.split(':')
    return list_invoice_payload[-1] == 'b'


async def succesfull_payment(message: Message):
    db = get_db(message)
    text_for_admins_part1, customer_email = get_customer_info(message)
    text_for_customer, text_for_admins_part2 = await prepare_data_for_succesfull_payment(message)
    await db.update_user_email(customer_email, message.from_user.id)
    if is_order_from_basket(message):
        await db.delete_all_items_from_basket(message.chat.id)
        try:
            remove_clear_basket_job(message, message.chat.id)
        except JobLookupError as err:
            logger.exception(err)
    amount = message.successful_payment.total_amount // 100
    currency = message.successful_payment.currency
    shipping_prices_text, total_shipping_price = get_shipping_data(message.successful_payment.shipping_option_id)
    text_for_customer += f'\n\nДоставка:\n{shipping_prices_text}\n' \
                         f'<b>Итого за доставку:</b> {total_shipping_price} {currency}\n\n'
    text_for_customer += f'<b>Итого вы оплатили:</b> {amount} {currency}.\n\n'\
                         f'{message_for_customer_with_addres(message)}'
    await message.answer(text=text_for_customer)
    text_for_admins_part3 = f'\n\nДоставка:\n{shipping_prices_text}\n'\
                            f'<b>Итого за доставку:</b> {total_shipping_price} {currency}\n\n'
    text_for_admins_part4 = f'<b>Итого оплачено:</b> {amount} {currency}\n\n' \
                            f'<b>telegram_payment_charge_id:</b> ' \
                            f'<code>{message.successful_payment.telegram_payment_charge_id}</code>\n' \
                            f'<b>provider_payment_charge_id:</b> ' \
                            f'<code>{message.successful_payment.provider_payment_charge_id}</code>'
    config = get_config(message)
    admin_ids = config.tg_bot.admin_ids
    for admin_id in admin_ids:
        await message.bot.send_message(
            text=text_for_admins_part1 + text_for_admins_part2 + text_for_admins_part3 + text_for_admins_part4,
            chat_id=admin_id)


def get_shipping_data(shipping_option_id: str) -> typing.Tuple[str, int]:
    shipping_option = ShippingOptions.get_shipping_option(shipping_option_id)
    shipping_title = shipping_option.title
    shipping_prices = shipping_option.prices
    shipping_prices_text = f"{shipping_title}:\n"
    total_shipping_price = 0
    for price in shipping_prices:
        shipping_prices_text += f'{price.label}: {int(price.amount / 100)} руб.\n'
        total_shipping_price += int(price.amount / 100)
    return shipping_prices_text, total_shipping_price


def message_for_customer_with_addres(message: Message) -> str:
    index = message.successful_payment.order_info.shipping_address.post_code
    country_code = message.successful_payment.order_info.shipping_address.country_code
    state = message.successful_payment.order_info.shipping_address.state
    city = message.successful_payment.order_info.shipping_address.city
    addres1 = message.successful_payment.order_info.shipping_address.street_line1
    addres2 = message.successful_payment.order_info.shipping_address.street_line2
    tel = message.successful_payment.order_info.phone_number
    if addres2:
        text = f'Ждите доставки по адресу: {country_code}, {index}, {state}, {city}, {addres1}, {addres2}. ' \
               f'Мы свяжемся с вами по телефону {tel} в ближайшее время.\n' \
               f'Если у вас есть вопросы, свяжитесь с нами по телефону: +79262270670 Анна. Доступны ' \
               f'telegram, whatsapp и голосовой звонок'
    else:
        text = f'Ждите доставки по адресу: {country_code}, {index}, {state}, {city}, {addres1}. ' \
               f'Мы свяжемся с вами по телефону {tel} в ближайшее время.\n' \
               f'Если у вас есть вопросы, свяжитесь с нами по телефону: +79262270670 Анна. Доступны ' \
               f'telegram, whatsapp и голосовой звонок'
    return text


def register_telegram_built_in_payments(dp: Dispatcher):
    dp.register_callback_query_handler(send_invoice, buy_item.filter(), ChatTypeFilter(types.ChatType.PRIVATE),
                                       state="*")
    dp.register_shipping_query_handler(choose_shipping)
    dp.register_pre_checkout_query_handler(process_pre_checkout_query)
    dp.register_message_handler(succesfull_payment, content_types=types.ContentType.SUCCESSFUL_PAYMENT)
