import datetime
import random

from tgbot.db_api.postgres_db import Database


async def fill_database(db: Database, id_start: int, id_finish: int):
    print(datetime.datetime.now(), 'Начало заполнения')
    i = id_start
    while i != id_finish + 1:
        await db.load_item_to_items(i, 'Специи', 1000, None, None, create_uniq_name(),
                                    ['AgACAgIAAxkBAAIY42GOiLoTTi7gkR0chZqGms1nAfLTAAL9'
                                     'tzEb0aNxSDpauxuH4UofAQADAgADeQADIgQ'],
                                    1000, 'Описание', 1, False, 'https://telegra.ph/file/238a58a13184ec03822a3.jpg')
        i += 1
    print(datetime.datetime.now(), 'Заполнено')


async def fill_database_new_categories(db: Database, id_start: int, id_finish: int):
    print(datetime.datetime.now(), 'Начало заполнения')
    i = id_start
    k = 1003
    while i != id_finish + 1:
        await db.load_item_to_items(i, create_uniq_name(), k, None, None, create_uniq_name(),
                                    ['AgACAgIAAxkBAAIY42GOiLoTTi7gkR0chZqGms1nAfLTAAL9'
                                     'tzEb0aNxSDpauxuH4UofAQADAgADeQADIgQ'],
                                    1000, 'Описание', 1, False, 'https://telegra.ph/file/238a58a13184ec03822a3.jpg')
        i += 1
        k += 1
    print(datetime.datetime.now(), 'Заполнено')


async def fill_database_new_subcategories(db: Database, id_start: int, id_finish: int):
    print(datetime.datetime.now(), 'Начало заполнения')
    i = id_start
    k = 2
    while i != id_finish + 1:
        d = int('1002' + str(k))
        await db.load_item_to_items(i, 'Новогодние подарки', 1002, create_uniq_name(), d, create_uniq_name(),
                                    ['AgACAgIAAxkBAAIY42GOiLoTTi7gkR0chZqGms1nAfLTAAL9'
                                     'tzEb0aNxSDpauxuH4UofAQADAgADeQADIgQ'],
                                    1000, 'Описание', 1, False, 'https://telegra.ph/file/238a58a13184ec03822a3.jpg')
        i += 1
        k += 1
    print(datetime.datetime.now(), 'Заполнено')


async def del_from_database(db: Database, id_start: int, id_finish: int):
    print(datetime.datetime.now(), 'Начало удаления')
    i = id_start
    for i in range(i, id_finish + 1):
        await db.del_item_from_items(i)
    print(datetime.datetime.now(), 'Удалено')


def create_uniq_name() -> str:
    letters = 'abcdefghijklmnopqrstuvwxyz'
    list_letters = list(letters)
    name = ''
    for i in range(10):
        name += random.choice(list_letters)
    return name
