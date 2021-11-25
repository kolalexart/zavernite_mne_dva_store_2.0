import typing

from aiogram import types
from aiogram.types import LabeledPrice


class ShippingOptions:

    ODI_SHIPPING = types.ShippingOption(
        id='odi',
        title='По городу Одинцово',
        prices=[
            LabeledPrice(label='Курьерская доставка',
                         amount=0),
        ]
    )

    PICKUP_SHIPPING = types.ShippingOption(
        id='pickup',
        title='Самовывоз',
        prices=[
            LabeledPrice(label='Самовывоз из магазина',
                         amount=0),
        ]
    )

    MOSCOW_SHIPPING = types.ShippingOption(
        id='moscow',
        title='По городу Москва',
        prices=[
            LabeledPrice(label='Курьерская доставка',
                         amount=300_00)
        ]
    )

    @classmethod
    def all_options_tuple(cls) -> typing.List[typing.Tuple[str, types.ShippingOption]]:
        return [(attribute, value) for attribute, value in cls.__dict__.items() if
                isinstance(value, types.ShippingOption)]

    @classmethod
    def all_options(cls) -> typing.List[types.ShippingOption]:
        return [value for attribute, value in cls.__dict__.items() if isinstance(value, types.ShippingOption)]

    @classmethod
    def price(cls, shipping_option_id: str) -> typing.Union[int, None]:
        amount = 0
        for option in cls.all_options():
            if option.id == shipping_option_id:
                for price in option.prices:
                    amount += price.amount
                return amount
        return

    @classmethod
    def get_shipping_option(cls, shipping_option_id: str) -> typing.Union[types.ShippingOption, None]:
        for option in cls.all_options():
            if option.id == shipping_option_id:
                return option
        return
