from aiogram.dispatcher.filters.state import StatesGroup, State


class AdminActions(StatesGroup):
    add_or_change = State()


class AddItem(StatesGroup):
    item_id = State()
    item_category_name = State()
    item_subcategory_name = State()
    item_name = State()
    item_photos = State()
    item_price = State()
    item_description = State()
    item_short_description = State()
    item_total_quantity = State()
    item_discontinued = State()
    item_photo_url = State()


class ChangeItem(StatesGroup):
    item_category_name = State()
    item_subcategory_name = State()
    item_name_choose = State()
    item_id = State()
    item_name_set = State()
    item_photos = State()
    item_main_photo = State()
    item_price = State()
    item_description = State()
    item_short_description = State()
    item_total_quantity = State()
    item_discontinued = State()
    item_photo_url = State()
    item_delete = State()


class DeleteItemCategory(StatesGroup):
    item_category_name = State()
    confirm = State()


class ChangeItemCategoryName(StatesGroup):
    item_category_name = State()
    new_item_category_name = State()


class DeleteItemSubCategory(StatesGroup):
    item_category_name = State()
    item_subcategory_name = State()
    confirm = State()


class ChangeItemSubCategoryName(StatesGroup):
    item_category_name = State()
    item_subcategory_name = State()
    new_item_subcategory_name = State()
