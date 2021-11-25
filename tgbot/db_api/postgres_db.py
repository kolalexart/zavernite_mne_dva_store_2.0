import datetime
import logging
from typing import Union, Optional, List

import asyncpg
from asyncpg import Pool, create_pool, Connection


logger = logging.getLogger(__name__)


async def delete_all_items_from_basket(dsn: str, telegram_id: int):
    connection: Connection = await asyncpg.connect(dsn, command_timeout=10)
    try:
        async with connection.transaction():
            sql = """DELETE FROM basket WHERE telegram_id=$1"""
            await connection.execute(sql, telegram_id)
    except Exception as err:
        logger.info(err)
    finally:
        await connection.close()


class Database:

    def __init__(self, url: str):
        self.pool: Union[Pool, None] = None
        self.url = url

    async def connect_to_database(self):
        self.pool = await create_pool(
            dsn=self.url
        )

    async def execute(self, command, *args,
                      fetch: bool = False,
                      fetchval: bool = False,
                      fetchrow: bool = False,
                      execute: bool = False
                      ):
        async with self.pool.acquire() as connection:
            connection: Connection
            async with connection.transaction():
                if fetch:
                    result = await connection.fetch(command, *args)
                if fetchval:
                    result = await connection.fetchval(command, *args)
                if fetchrow:
                    result = await connection.fetchrow(command, *args)
                if execute:
                    result = await connection.execute(command, *args)
            return result

    async def drop_table(self, table_name: str):
        sql = f'DROP TABLE IF EXISTS {table_name} CASCADE'
        await self.execute(sql, execute=True)

    async def del_all_items_from_table(self, table_name: str):
        sql = f'DELETE FROM {table_name} WHERE TRUE'
        await self.execute(sql, execute=True)

    async def select_all_items_from_table(self, table_name: str):
        sql = f'SELECT * FROM {table_name}'
        return await self.execute(sql, fetch=True)

    async def count_items_from_table(self, table: str):
        sql = f'SELECT COUNT(*) FROM {table}'
        return await self.execute(sql, fetchval=True)

    @staticmethod
    def format_args(table_name: str, parameters: dict):
        sql = f'SELECT * FROM {table_name} WHERE ' + \
              f' AND '.join([f'{item}=${num}' for num, item in enumerate(parameters, start=1)])
        return sql, tuple(parameters.values())

    async def select_item_from_table(self, table_name: str, **kwargs):
        sql, parameters = self.format_args(table_name, kwargs)
        return await self.execute(sql, *parameters, fetchrow=True)

    async def create_table_users(self):
        sql = """CREATE TABLE IF NOT EXISTS users(
        telegram_id bigint NOT NULL UNIQUE PRIMARY KEY,
        username varchar(100) NULL,
        full_name varchar(100) NOT NULL,
        email varchar(100) NULL,
        first_login_time timestamp NOT NULL,
        referer_telegram_id bigint NULL
        )"""
        await self.execute(sql, execute=True)

    async def add_new_user(self, telegram_id: int, username: Optional[str], full_name: str, email: Optional[str],
                           first_login_time: datetime.datetime, referer_telegram_id: Optional[int]):
        sql = 'INSERT INTO users VALUES ($1, $2, $3, $4, $5, $6) RETURNING *'
        return await self.execute(sql, telegram_id, username, full_name, email, first_login_time, referer_telegram_id,
                                  fetchrow=True)

    async def del_user(self, telegram_id: int):
        sql = 'DELETE FROM users WHERE telegram_id=$1'
        await self.execute(sql, telegram_id, execute=True)

    async def update_user_email(self, email: str, telegram_id: int):
        sql = 'UPDATE users SET email=$1 WHERE telegram_id=$2'
        await self.execute(sql, email, telegram_id, execute=True)

    async def create_table_items(self):
        sql = """CREATE TABLE IF NOT EXISTS items (
        item_id serial PRIMARY KEY,
        item_category_name varchar(30) NOT NULL,
        item_category_code int NOT NULL,
        item_subcategory_name varchar(30) NULL,
        item_subcategory_code int NULL,
        item_name varchar(30) NOT NULL UNIQUE,
        item_photos varchar(100) ARRAY NOT NULL,
        item_price integer NOT NULL,
        item_description text NOT NULL,
        item_short_description varchar(80) NULL,
        item_total_quantity smallint NOT NULL,
        item_discontinued boolean NOT NULL,
        item_photo_url varchar(255) NOT NULL
        );"""
        await self.execute(sql, execute=True)

    async def get_categories_from_items(self, for_admins: bool = False):
        if for_admins:
            sql = """SELECT DISTINCT item_category_name, item_category_code FROM items ORDER BY item_category_name"""
        else:
            sql = """SELECT DISTINCT item_category_name, item_category_code FROM items WHERE item_discontinued=FALSE 
            AND item_total_quantity>0 ORDER BY item_category_name"""
        return await self.execute(sql, fetch=True)

    async def count_categories(self) -> Union[int, None]:
        sql = 'SELECT COUNT(DISTINCT item_category_name) FROM items'
        result = await self.execute(sql, fetchval=True)
        return result if result else None

    async def count_subcategories(self, item_category_code: int) -> Union[int, None]:
        sql = 'SELECT COUNT(DISTINCT item_subcategory_name) FROM items WHERE item_category_code=$1'
        result = await self.execute(sql, item_category_code, fetchval=True)
        return result if result else None

    async def count_items(self, item_category_code: int, item_subcategory_code: Optional[int] = None,
                          for_admins: bool = False):
        if for_admins:
            if item_subcategory_code:
                sql = """SELECT COUNT(*) FROM items WHERE item_category_code=$1 AND item_subcategory_code=$2"""
                return await self.execute(sql, item_category_code, item_subcategory_code, fetchval=True)
            else:
                sql = """SELECT COUNT(*) FROM items WHERE item_category_code=$1"""
                return await self.execute(sql, item_category_code, fetchval=True)
        else:
            if item_subcategory_code:
                sql = """SELECT COUNT(*) FROM items WHERE item_category_code=$1 AND item_subcategory_code=$2 AND 
                item_discontinued=FALSE AND item_total_quantity>0"""
                return await self.execute(sql, item_category_code, item_subcategory_code, fetchval=True)
            else:
                sql = """SELECT COUNT(*) FROM items WHERE item_category_code=$1 AND item_discontinued=FALSE AND 
                item_total_quantity>0"""
                return await self.execute(sql, item_category_code, fetchval=True)

    async def get_subcategories_from_items(self, item_category_code: int, for_admis: bool = False):
        if for_admis:
            sql = """SELECT DISTINCT item_subcategory_name, item_subcategory_code FROM items WHERE item_category_code=$1
            ORDER BY item_subcategory_name"""
        else:
            sql = """SELECT DISTINCT item_subcategory_name, item_subcategory_code FROM items WHERE item_category_code=$1 
            AND item_discontinued=FALSE AND item_total_quantity>0 ORDER BY item_subcategory_name"""
        return await self.execute(sql, item_category_code, fetch=True)

    async def get_items_from_items(self, item_category_code: int, item_subcategory_code: Optional[int] = None,
                                   for_admins: bool = False):
        if item_subcategory_code:
            if for_admins:
                sql = """SELECT * FROM items WHERE item_category_code=$1 AND item_subcategory_code=$2 
                ORDER BY item_name"""
            else:
                sql = """SELECT * FROM items WHERE item_category_code=$1 AND item_subcategory_code=$2 AND 
                item_discontinued=FALSE AND item_total_quantity>0 ORDER BY item_name"""
            return await self.execute(sql, item_category_code, item_subcategory_code, fetch=True)
        else:
            if for_admins:
                sql = """SELECT * FROM items WHERE item_category_code=$1 ORDER BY item_name"""
            else:
                sql = """SELECT * FROM items WHERE item_category_code=$1 AND
                item_discontinued=FALSE AND item_total_quantity>0 ORDER BY item_name"""
            return await self.execute(sql, item_category_code, fetch=True)

    async def get_item_from_items(self, item_id: int):
        sql = 'SELECT * FROM items WHERE item_id=$1'
        return await self.execute(sql, item_id, fetchrow=True)

    async def get_items_ids_from_items(self):
        sql = 'SELECT item_id FROM items ORDER BY item_id'
        return await self.execute(sql, fetch=True)

    async def get_items_names_from_items(self):
        sql = 'SELECT item_name FROM items ORDER BY item_name'
        return await self.execute(sql, fetch=True)

    async def load_item_to_items(self,
                                 item_id: Optional[int],
                                 item_category_name: str,
                                 item_category_code: int,
                                 item_subcategory_name: Optional[str],
                                 item_subcategory_code: Optional[int],
                                 item_name: str,
                                 item_photos: List[str],
                                 item_price: int,
                                 item_description: str,
                                 item_short_description: Optional[str],
                                 item_total_quantity: int,
                                 item_discontinued: bool,
                                 item_photo_url: str
                                 ):
        if item_id:
            sql = "INSERT INTO items VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) RETURNING *"
            return await self.execute(sql, item_id, item_category_name, item_category_code, item_subcategory_name,
                                      item_subcategory_code, item_name, item_photos, item_price, item_description,
                                      item_short_description, item_total_quantity, item_discontinued, item_photo_url,
                                      fetchrow=True)
        else:
            sql = "INSERT INTO items VALUES (DEFAULT, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING *"
            return await self.execute(sql, item_category_name, item_category_code, item_subcategory_name,
                                      item_subcategory_code, item_name, item_photos, item_price, item_description,
                                      item_short_description, item_total_quantity, item_discontinued, item_photo_url,
                                      fetchrow=True)

    async def select_items_like(self, name_starts_with: str):
        sql = f"SELECT * FROM items WHERE item_name ILIKE '{name_starts_with}%' AND " \
              f"item_discontinued=FALSE and items.item_total_quantity>0"
        return await self.execute(sql, fetch=True)

    async def update_item_from_items(self, item_id, parameter, value):
        sql = f"""UPDATE items SET {parameter}=$1 WHERE item_id=$2"""
        await self.execute(sql, value, item_id, execute=True)

    async def update_item_first_photo_from_items(self, item_id, value):
        sql = 'UPDATE items SET item_photos[1] = $1 WHERE item_id=$2'
        await self.execute(sql, value, item_id, execute=True)

    async def del_item_from_items(self, item_id: int):
        sql = """DELETE FROM items WHERE item_id=$1"""
        await self.execute(sql, item_id, execute=True)

    @staticmethod
    def format_args_for_deleting_items(parameters: dict):
        sql = f'DELETE FROM items WHERE ' + \
              f' AND '.join([f'{item}=${num}' for num, item in enumerate(parameters, start=1)])
        sql += ' RETURNING *'
        return sql, tuple(parameters.values())

    async def delete_items_from_items(self, **kwargs):
        sql, parameters = self.format_args_for_deleting_items(kwargs)
        deleted_items = await self.execute(sql, *parameters, fetch=True)
        return len(deleted_items)

    @staticmethod
    def format_args_for_updating_items(target: str, parameters: dict):
        sql = f'UPDATE items SET {target}=$1 WHERE ' + \
              f' AND '.join([f'{item}=${num}' for num, item in enumerate(parameters, start=2)])
        sql += ' RETURNING *'
        return sql, tuple(parameters.values())

    async def update_items_from_items(self, target: str, new_value, **kwargs):
        sql, parameters = self.format_args_for_updating_items(target, kwargs)
        updated_items = await self.execute(sql, new_value, *parameters, fetch=True)
        return len(updated_items)

    async def create_table_basket(self):
        sql = """CREATE TABLE IF NOT EXISTS basket (
        telegram_id bigint NOT NULL,
        item_id integer NOT NULL,
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
        FOREIGN KEY (item_id) REFERENCES items(item_id),
        quantity smallint NOT NULL ,
        added_at timestamp NOT NULL
        )"""
        await self.execute(sql, execute=True)

    async def add_items_to_basket(self, telegram_id: int, item_id: int, quantity: int, added_at: datetime.datetime):
        sql = 'INSERT INTO basket VALUES ($1, $2, $3, $4)'
        await self.execute(sql, telegram_id, item_id, quantity, added_at, execute=True)
        sql = """SELECT users.full_name, basket.item_id, items.item_name, basket.quantity, added_at FROM basket
        JOIN users ON basket.telegram_id = users.telegram_id
        JOIN items ON basket.item_id = items.item_id
        WHERE basket.telegram_id=$1 AND basket.item_id=$2 AND added_at = (SELECT MAX(added_at) FROM basket)
        """
        return await self.execute(sql, telegram_id, item_id, fetchrow=True)

    async def select_items_from_basket(self, telegram_id: int):
        sql = """SELECT users.full_name, basket.item_id, items.item_name, basket.quantity, items.item_price, added_at 
        FROM basket
        JOIN users USING (telegram_id)
        JOIN items USING (item_id)
        WHERE telegram_id=$1
        ORDER BY added_at
        """
        return await self.execute(sql, telegram_id, fetch=True)

    async def delete_item_from_basket(self, telegram_id: int, item_id: int):
        sql = """DELETE FROM basket WHERE telegram_id=$1 AND item_id=$2"""
        await self.execute(sql, telegram_id, item_id, execute=True)

    async def delete_all_items_from_basket(self, telegram_id: int):
        sql = """DELETE FROM basket WHERE telegram_id=$1"""
        await self.execute(sql, telegram_id, execute=True)

    async def select_item_from_basket(self, telegram_id: int, item_id: int):
        try:
            sql = """SELECT users.full_name, basket.item_id, items.item_name, basket.quantity, items.item_price, 
            added_at FROM basket
            JOIN users ON basket.telegram_id = users.telegram_id
            JOIN items ON basket.item_id = items.item_id
            WHERE basket.telegram_id=$1 AND basket.item_id=$2
            """
            return await self.execute(sql, telegram_id, item_id, fetchrow=True)
        except UnboundLocalError:
            return None

    async def change_quantity_item_in_basket(self, telegram_id: int, item_id: int, new_quantity: int,
                                             new_added_at: datetime.datetime):
        sql = """UPDATE basket SET quantity=$3, added_at=$4 WHERE telegram_id=$1 AND item_id=$2"""
        await self.execute(sql, telegram_id, item_id, new_quantity, new_added_at, execute=True)
        sql = """SELECT users.full_name, basket.item_id, items.item_name, basket.quantity, items.item_price, added_at 
        FROM basket
        JOIN users ON basket.telegram_id = users.telegram_id
        JOIN items ON basket.item_id = items.item_id
        WHERE basket.telegram_id=$1 AND basket.item_id=$2 AND added_at = (SELECT MAX(added_at) FROM basket)
        """
        return await self.execute(sql, telegram_id, item_id, fetchrow=True)
