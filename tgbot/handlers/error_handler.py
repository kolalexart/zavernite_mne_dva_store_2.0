import logging

from aiogram import Dispatcher
from aiogram.utils.exceptions import TelegramAPIError, MessageNotModified, CantParseEntities

logger = logging.getLogger(__name__)


async def errors_handler(update, exception):
    """
    Exceptions handler. Catches all exceptions within task factory tasks.
    :param update:
    :param exception:
    :return: stdout logging
    """

    if isinstance(exception, MessageNotModified):
        logging.exception('Message is not modified: %s\nUpdate: %s', exception, update)
        return True

    if isinstance(exception, CantParseEntities):
        logging.exception(f'CantParseEntities: %s\nUpdate: %s', exception, update)
        return True

    if isinstance(exception, TelegramAPIError):
        logger.exception(f'TelegramAPIError: %s\nUpdate: %s', exception, update)
        return True

    logger.exception('Update: %s\nException: %s', update, exception)


def register_error(dp: Dispatcher):
    dp.register_errors_handler(errors_handler)
