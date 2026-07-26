from aiogram import Router
from aiogram.types import Message
from aiogram.filters import StateFilter

from database import get_custom_button_response

router = Router()


@router.message(StateFilter(None))
async def custom_button_catch_all(message: Message):
    """Admin panel orqali yaratilgan maxsus tugmalarga javob beradi.
    Bu handler eng oxirida ro'yxatdan o'tkaziladi — shuning uchun boshqa
    hech qanday tugma/handler mos kelmagan taqdirdagina ishga tushadi."""
    if not message.text:
        return
    response = await get_custom_button_response(message.text)
    if response:
        await message.answer(response)
