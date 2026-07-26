import datetime
import random

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter

from config import WHEEL_PRIZES, WHEEL_COOLDOWN_HOURS
from database import get_user, add_coins, grant_vip, set_wheel_spin

router = Router()


@router.message(F.text == "🎡 Omad g'ildiragi", StateFilter(None))
async def wheel_spin(message: Message):
    user = await get_user(message.from_user.id)
    now = datetime.datetime.now()

    if user and user["last_wheel_spin"]:
        try:
            last_spin = datetime.datetime.fromisoformat(user["last_wheel_spin"])
            next_spin = last_spin + datetime.timedelta(hours=WHEEL_COOLDOWN_HOURS)
            if now < next_spin:
                remaining = next_spin - now
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes = remainder // 60
                await message.answer(
                    f"⏳ Siz allaqachon aylantirgansiz!\n"
                    f"Keyingi imkoniyat: <b>{hours} soat {minutes} daqiqadan</b> keyin.",
                    parse_mode="HTML",
                )
                return
        except ValueError:
            pass

    await message.answer("🎡 G'ildirak aylanmoqda...")

    prize = random.choice(WHEEL_PRIZES)
    await set_wheel_spin(message.from_user.id)

    if prize["type"] == "coin":
        await add_coins(message.from_user.id, prize["amount"])
    elif prize["type"] == "vip":
        await grant_vip(message.from_user.id, prize["amount"])

    await message.answer(
        f"🎉 <b>Tabriklaymiz!</b>\n\n"
        f"🎁 Sizning yutug'ingiz: <b>{prize['label']}</b>\n\n"
        f"⏱ Keyingi imkoniyat {WHEEL_COOLDOWN_HOURS} soatdan keyin!",
        parse_mode="HTML",
    )
