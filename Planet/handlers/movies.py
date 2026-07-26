from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config import CATEGORIES, COIN_FOR_WATCH
from database import (
    get_movie_by_code, random_movie, increment_views, mark_watched, add_coins,
)
from keyboards.inline import movie_action_buttons
from states import MovieSearch

router = Router()

# tugma matni -> kategoriya kaliti (masalan "👻 Ujas kinolar" -> "ujas")
CATEGORY_BY_BUTTON = {v: k for k, v in CATEGORIES.items()}


async def _deliver_movie(message: Message, movie) -> None:
    """Topilgan kino yozuvini foydalanuvchiga yuboradi va coin/statistika yangilaydi."""
    code = movie["code"]
    title = movie["title"] or "Nomsiz kino"

    await increment_views(code)

    is_new_watch = await mark_watched(message.from_user.id, code)
    coin_note = ""
    if is_new_watch:
        await add_coins(message.from_user.id, COIN_FOR_WATCH)
        coin_note = f"\n\n🪙 +{COIN_FOR_WATCH} Coin qo'shildi!"

    caption = f"🎬 {title}\n🔢 Kod: {code}{coin_note}"

    try:
        await message.answer_video(
            video=movie["file_id"],
            caption=caption,
            reply_markup=movie_action_buttons(code),
        )
    except Exception:
        # Agar file_id video sifatida yuborilmasa (masalan document bo'lsa)
        await message.answer_document(
            document=movie["file_id"],
            caption=caption,
            reply_markup=movie_action_buttons(code),
        )


# ------------------------------------------------------------------
# Kategoriya tugmalari bosilganda -> kino kodi so'raladi
# ------------------------------------------------------------------
@router.message(F.text.in_(set(CATEGORIES.values())), StateFilter(None))
async def choose_category(message: Message, state: FSMContext):
    category_key = CATEGORY_BY_BUTTON.get(message.text)
    await state.update_data(category=category_key)
    await state.set_state(MovieSearch.waiting_code)
    await message.answer(
        f"{message.text}\n\n🔢 Ko'rmoqchi bo'lgan kinongizning kodini yuboring:"
    )


@router.message(MovieSearch.waiting_code)
async def search_in_category(message: Message, state: FSMContext):
    code = message.text.strip()
    await state.clear()

    if not code:
        await message.answer("❌ Kod bo'sh bo'lishi mumkin emas.")
        return

    movie = await get_movie_by_code(code)
    if movie:
        await _deliver_movie(message, movie)
    else:
        await message.answer(f"❌ Kechirasiz, <code>{code}</code> kodli kino topilmadi.", parse_mode="HTML")


# ------------------------------------------------------------------
# Har qanday joyda raqamli kod yuborilsa (bo'lim tanlanmagan bo'lsa ham)
# ------------------------------------------------------------------
@router.message(F.text.regexp(r"^\d+$"), StateFilter(None))
async def search_movie_by_code_global(message: Message):
    code = message.text.strip()
    movie = await get_movie_by_code(code)
    if movie:
        await _deliver_movie(message, movie)
    else:
        await message.answer(f"❌ Kechirasiz, <code>{code}</code> kodli kino topilmadi.", parse_mode="HTML")


# ------------------------------------------------------------------
# Tasodifiy kino
# ------------------------------------------------------------------
@router.message(F.text == "🎲 Tasodifiy kino", StateFilter(None))
async def random_movie_handler(message: Message):
    movie = await random_movie()
    if movie:
        await _deliver_movie(message, movie)
    else:
        await message.answer("🍿 Afsuski, hozircha bazada birorta ham kino yo'q.")


# ------------------------------------------------------------------
# Coin ishlash (ma'lumot)
# ------------------------------------------------------------------
@router.message(F.text == "🪙 Coin ishlash", StateFilter(None))
async def coin_info(message: Message):
    me = await message.bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{message.from_user.id}"
    text = (
        "🪙 <b>Coin ishlash yo'llari</b>\n\n"
        "• Botga birinchi marta start bergani uchun: <b>+1 Coin</b>\n"
        "• Kinoni ochib ko'rgani uchun (har bir kino uchun 1 marta): <b>+5 Coin</b>\n"
        "• Do'stingizni taklif qilsangiz: <b>+50 Coin</b>\n\n"
        f"🔗 Sizning referal havolangiz:\n{ref_link}\n\n"
        "Yig'ilgan coinlarni 💎 VIP obunaga almashtirishingiz mumkin!"
    )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
