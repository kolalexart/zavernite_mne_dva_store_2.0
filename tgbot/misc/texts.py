import typing

from tgbot.misc.secondary_functions import User, Item, ItemInBasket


class UserTexts:

    PHOTO_LOGO = 'AgACAgIAAxkBAANDYXQ04ysmoq651-Pz5Go0AZq-AgEAAk63MRuX3KBLy3Tcto6m0FUBAAMCAAN5AAMhBA'

    USER_HELP = 'Вы находитесь в разделе "Помощь"🆘\n\n' \
                'Навигация в боте возможна при помощи команд, либо при помощи всплывающих кнопок.\n\n' \
                'Для того, чтобы воспользоваться командой, вы можете нажать на синий текст, начинающийся с ' \
                'символа "/". Либо можно нажать синюю кнопку "menu" в нижнем левом углу вашего экрана, если вы ' \
                'заходите с мобильного устройства📱, или нажать кнопку с символом "/" в нижнем правом углу экрана, ' \
                'если вы заходите с компьютера💻\n\n' \
                'Доступны следующие команды:\n\n'\
                '/start - перезапустить бота. Данную команду можно выполнить в любом пункте меню. Например, если вы ' \
                'запутались и хотите переместиться в самое начало - в главное меню;\n\n'\
                '/menu - переместиться в каталог и начать покупки;\n\n'\
                '/help - переместиться в настоящий раздел.'

    USER_ABOUT_US = 'Мы те, кто понимают, что подарки могут быть бесконечно разнообразными и интересными, ' \
                    'независимо от бюджета💸\n\nМы те, кто стремятся придать красоту и эстетику даже самому простому ' \
                    'предмету нашего быта, готовящегося стать подарком🌷\n\nМы те, кто смогут сделать любой подарок, ' \
                    'как минимум, уникально оформленным🎁\n\nА еще мы помогаем дарить близким радость и самые теплые ' \
                    'эмоции, передавая их от вас за многие километры🧡'

    USER_BACK_TO_MAIN_MENU = 'Вы в главном меню. Выберите необходимую кнопку:'

    USER_LEGAL_INFORMATION = 'Магазин: "Заверните мне два"\n\n' \
                             'Название компании: \n' \
                             'ИНН: \n' \
                             'ОГРНИП: \n' \
                             'Номер счёта: \n' \
                             'Банк: \n' \
                             'БИК: \n' \
                             'Кор. счёт: \n' \
                             'Телефон: \n' \
                             'Почта: \n' \
                             'Юр. адрес: '

    USER_MENU = 'Вот, что у нас есть:'

    USER_BACK_TO_CATALOG = 'Вы перемещены в начало каталога. Можете продолжить покупки '\
                           'или перейдите в корзину для оплаты'

    USER_BASKET_PAY_OR_CLEAR = 'Если все верно, то нажмите "Оплатить".\n' \
                               'Если нет, очистите корзину либо выберите позицию, которую хотите удалить:'

    USER_BASKET_EMPTY = 'В корзине больше не осталось товаров.\n' \
                        'Вы перемещены в начало каталога. Можете продолжить покупки'

    USER_BASKET_CANCEL_WITH_GOODS = 'Вы вышли из корзины, но товары в ней будут храниться еще 24 часа '\
                                    'или до тех пор, пока вы все из нее не удалите.\n'\
                                    'Вы перемещены в начало каталога. Можете продолжить покупки'

    USER_BASKET_CANCEL_WITHOUT_GOODS = 'Ваша корзина очищена.\nВы перемещены в начало каталога. ' \
                                       'Можете продолжить покупки'

    USER_BASKET_CANCEL_AFTER_24_HOURS = 'Прошло больше 24 часов и ваша корзина уже очищена.\n'\
                                        'Вы перемещены в начало каталога. Можете продолжить покупки'

    @staticmethod
    def user_hello_old_user(user: User) -> str:
        text = f'Привет, {user.full_name}!\n\n' \
               f'Вы были зарегистрированы в боте ранее и можете сразу перейти ' \
               f'в каталог для покупок либо выберите другой пункт меню:'
        return text

    @staticmethod
    def user_hello_new_user(user: User, referer: typing.Optional[User]) -> str:
        if referer:
            text = f'Привет, {user.full_name}!\n\n' \
                   f'Вы были только что зарегистрированы ботом. Вас привел {referer.full_name}. Можете перейти ' \
                   f'в каталог для покупок либо выберите другой пункт меню:'
        else:
            text = f'Привет, {user.full_name}!\n\n' \
                   f'Вы были только что зарегистрированы ботом. Можете перейти ' \
                   f'в каталог для покупок либо выберите другой пункт меню:'
        return text

    @staticmethod
    def item_text(item: Item) -> str:
        text = f'<b>"{item.item_name}"</b>\n'\
               f'<b>Цена: {item.item_price} руб.</b>\n\n'\
               f'Количество на складе: {item.item_total_quantity} шт.\n\n'\
               f'{item.item_description}'
        return text

    @staticmethod
    def user_successful_adding_to_basket(item_in_basket: ItemInBasket, quantity: int) -> str:
        text = f'{item_in_basket.full_name}, вы успешно добавили в корзину '\
               f'товар с id {item_in_basket.item_id} "{item_in_basket.item_name}" ' \
               f'в количестве {quantity} шт. Всего в корзине {item_in_basket.quantity} шт. данного товара'
        return text

    @staticmethod
    def user_unsuccessful_adding_to_basket(item_in_basket: ItemInBasket, quantity: int, item_total_quantity: int) \
            -> str:
        text = f'У вас в корзине {item_in_basket.quantity} шт. "{item_in_basket.item_name}". Вы пытаетесь добавить ' \
               f'еще {quantity} шт. На складе осталось только {item_total_quantity} шт. Поэтому ' \
               f'вы можете добавить еще не больше {item_total_quantity - item_in_basket.quantity}'
        return text

    @staticmethod
    def user_basket_title(full_name: str) -> str:
        text = f'{full_name}, в вашей корзине следующие товары:\n'
        return text

    @staticmethod
    def user_basket_item(index: int, item_in_basket: ItemInBasket) -> str:
        text = f'{index}. id={item_in_basket.item_id} - <b>"{item_in_basket.item_name}"</b> - ' \
               f'{item_in_basket.item_price} руб. - {item_in_basket.quantity} шт. - ' \
               f'<b>Сумма: {item_in_basket.item_price * item_in_basket.quantity} руб.</b>\n'
        return text

    @staticmethod
    def user_basket_summary(total_sum: int) -> str:
        text = f'\n<b>Итого: {total_sum} руб.</b>\n\n'
        return text

    @staticmethod
    def user_basket_deleted_item(item_id: int):
        text = f'Позиция с id={item_id} удалена.'
        return text


class AdminTexts:
    pass
