import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from config import COIN_FOR_START, COIN_FOR_REFERRAL
from database import (
    add_user, get_user, add_coins, add_referral, check_and_expire_vip,
)
from keyboards.reply import get_main_menu

router = Router()


@router.message(CommandStart(), StateFilter(None))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    referred_by = None
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_part = args[1].replace("ref_", "").strip()
        if ref_part.isdigit() and int(ref_part) != message.from_user.id:
            referred_by = int(ref_part)

    is_new = await add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        referred_by=referred_by,
    )

    if is_new:
        await add_coins(message.from_user.id, COIN_FOR_START)
        if referred_by:
            referrer = await get_user(referred_by)
            if referrer:
                await add_coins(referred_by, COIN_FOR_REFERRAL)
                await add_referral(referred_by)
                try:
                    await message.bot.send_message(
                        referred_by,
                        f"🎉 Sizning taklifingiz bilan yangi foydalanuvchi qo'shildi!\n"
                        f"🪙 Sizga +{COIN_FOR_REFERRAL} Coin berildi!",
                    )
                except Exception:
                    pass

    welcome_text = (
        f"👋 Xush kelibsiz, <b>{message.from_user.first_name}</b>!\n\n"
        "🎬 <b>O'zbekistondagi eng ulkan kino-botga xush kelibsiz.</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang yoki to'g'ridan-to'g'ri kino kodini yuboring:"
    )

    await message.answer(
        welcome_text,
        reply_markup=await get_main_menu(message.from_user.id),
        parse_mode="HTML",
    )
    if is_new:
        await message.answer(f"🎁 Botga xush kelibsiz sovg'asi: +{COIN_FOR_START} Coin!")


@router.message(F.text == "⬅️ Bosh menyu", StateFilter(None))
async def back_to_main_menu(message: Message):
    await message.answer("🏠 Bosh menyu:", reply_markup=await get_main_menu(message.from_user.id))


@router.message(F.text == "👤 Profil", StateFilter(None))
async def show_profile(message: Message):
    user = await get_user(message.from_user.id)
    is_vip = await check_and_expire_vip(message.from_user.id)

    if user:
        coins = user["coins"]
        streak = user["streak"]
        referrals = user["referrals"]
        vip_expire = user["vip_expire"]
    else:
        coins, streak, referrals, vip_expire = 0, 1, 0, None

    if is_vip and vip_expire:
        try:
            exp_dt = datetime.datetime.fromisoformat(vip_expire)
            vip_status = f"💎 VIP a'zo (muddati: {exp_dt.strftime('%d.%m.%Y %H:%M')} gacha)"
        except ValueError:
            vip_status = "💎 VIP a'zo"
    else:
        vip_status = "🆓 Bepul obuna"

    me = await message.bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{message.from_user.id}"

    profile_info = (
        f"👤 <b>Sizning Profilingiz:</b>\n\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"👤 <b>Ism:</b> {message.from_user.full_name}\n"
        f"🪙 <b>Coinlar:</b> {coins} ball\n"
        f"👑 <b>Status:</b> {vip_status}\n"
        f"🔥 <b>Streak:</b> {streak} kun\n"
        f"🤝 <b>Taklif qilingan do'stlar:</b> {referrals} ta\n\n"
        f"🔗 <b>Referal havolangiz:</b>\n{ref_link}"
    )
    await message.answer(profile_info, parse_mode="HTML", disable_web_page_preview=True)
