from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config import VIP_COIN_PRICE, VIP_COIN_DAYS, VIP_MONTHLY_DAYS, VIP_MONTHLY_PRICE_TEXT
from database import spend_coins, grant_vip, redeem_promo
from keyboards.inline import vip_purchase_buttons
from states import RedeemPromo

router = Router()


@router.message(F.text == "💎 VIP obuna", StateFilter(None))
async def vip_menu(message: Message):
    text = (
        "💎 <b>VIP obuna</b>\n\n"
        "VIP imkoniyatlari:\n"
        "• Reklamasiz ko'rish\n"
        "• VIP premyeralarga kirish\n"
        "• Yuqori sifat (1080p, 4K)\n\n"
        "Quyidagi usullardan birini tanlang:"
    )
    await message.answer(text, reply_markup=vip_purchase_buttons(), parse_mode="HTML")


@router.callback_query(F.data == "vip_buy_money")
async def vip_buy_money(call: CallbackQuery):
    await call.message.answer(
        f"💳 <b>1 Oylik VIP — {VIP_MONTHLY_PRICE_TEXT}</b>\n\n"
        "To'lovni amalga oshirish uchun admin bilan bog'laning. "
        "To'lov qilinganidan so'ng admin sizga VIP statusni faollashtirib beradi.",
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "vip_buy_coins")
async def vip_buy_coins(call: CallbackQuery):
    success = await spend_coins(call.from_user.id, VIP_COIN_PRICE)
    if not success:
        await call.message.answer(
            f"❌ Coiningiz yetarli emas!\n\n"
            f"💎 VIP olish uchun kerak: <b>{VIP_COIN_PRICE} Coin</b>",
            parse_mode="HTML",
        )
        await call.answer()
        return

    new_expire = await grant_vip(call.from_user.id, VIP_COIN_DAYS)
    await call.message.answer(
        f"🎉✨ <b>Tabriklaymiz!</b> ✨🎉\n\n"
        f"💎 Sizga <b>{VIP_COIN_DAYS} kunlik VIP</b> berildi!\n"
        f"📅 Amal qilish muddati: <b>{new_expire.strftime('%d.%m.%Y %H:%M')}</b> gacha",
        parse_mode="HTML",
    )
    await call.answer("✅ VIP faollashtirildi!")


@router.callback_query(F.data == "vip_promo")
async def vip_promo_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(RedeemPromo.code)
    await call.message.answer("🎟 Promo kodni kiriting:")
    await call.answer()


@router.message(RedeemPromo.code)
async def vip_promo_check(message: Message, state: FSMContext):
    code = message.text.strip()
    await state.clear()

    success, result = await redeem_promo(code, message.from_user.id)

    if success:
        days = result
        await message.answer(
            f"🎉✨ <b>PROMO KOD QABUL QILINDI!</b> ✨🎉\n\n"
            f"💎 Sizga <b>{days} kunlik VIP</b> qo'shildi!\n"
            f"Rahmat! 🥳",
            parse_mode="HTML",
        )
    else:
        reasons = {
            "notfound": "❌ Bunday promo kod topilmadi yoki faol emas.",
            "limit": "❌ Bu promo kodning ishlatilish limiti tugagan.",
            "already_used": "❌ Siz bu promo kodni allaqachon ishlatgansiz.",
        }
        await message.answer(reasons.get(result, "❌ Xatolik yuz berdi."))
