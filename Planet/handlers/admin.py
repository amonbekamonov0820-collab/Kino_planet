import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config import ADMIN_ADD_BUTTONS, CATEGORIES, PROMO_DEFAULT_DAYS, PROMO_DEFAULT_USES
from database import (
    is_admin, add_admin, remove_admin, get_db_admin_ids, get_all_admin_ids,
    add_movie, next_auto_code, get_movie_by_code,
    list_movies, count_movies, update_movie_title, update_movie_video, delete_movie,
    create_promo,
    get_stats, users_joined_today, users_joined_this_month,
    create_custom_button, get_custom_buttons, delete_custom_button,
    all_user_ids,
)
from keyboards.reply import get_admin_menu
from keyboards.inline import (
    admin_remove_list_buttons, custom_buttons_manage_list,
    movie_category_filter_buttons, movie_list_buttons, movie_detail_buttons,
    movie_delete_confirm_buttons,
)
from states import AddMovie, AddAdmin, CreatePromo, CreateButton, Broadcast, EditMovieTitle, EditMovieVideo

router = Router()

MOVIES_PAGE_SIZE = 8


async def _admin_only(message: Message) -> bool:
    if not await is_admin(message.from_user.id):
        return False
    return True


# ------------------------------------------------------------------
# Admin panelga kirish
# ------------------------------------------------------------------
@router.message(F.text == "⚙️ Admin Panel", StateFilter(None))
async def admin_panel(message: Message):
    if not await _admin_only(message):
        return
    await message.answer("🏠 <b>Admin Panel</b>\n\nKerakli bo'limni tanlang:", reply_markup=get_admin_menu(), parse_mode="HTML")


# ------------------------------------------------------------------
# Admin qo'shish / o'chirish
# ------------------------------------------------------------------
@router.message(F.text == "➕ Admin qo'shish", StateFilter(None))
async def add_admin_start(message: Message, state: FSMContext):
    if not await _admin_only(message):
        return
    await state.set_state(AddAdmin.user_id)
    await message.answer("🔢 Yangi admin qilmoqchi bo'lgan foydalanuvchining Telegram ID raqamini yuboring:")


@router.message(AddAdmin.user_id)
async def add_admin_finish(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Iltimos, faqat raqamli ID yuboring.")
        return

    new_admin_id = int(text)
    await add_admin(new_admin_id, message.from_user.id)

    await message.answer(
        f"✅✨ <b>Admin muvaffaqiyatli qo'shildi!</b> ✨✅\n\n🆔 <code>{new_admin_id}</code>",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )
    try:
        await message.bot.send_message(
            new_admin_id,
            "🎉 Tabriklaymiz! Siz botga admin etib tayinlandingiz.\n"
            "Admin panelga kirish uchun /start bosing.",
        )
    except Exception:
        pass


@router.message(F.text == "➖ Admin o'chirish", StateFilter(None))
async def remove_admin_list(message: Message):
    if not await _admin_only(message):
        return
    db_admins = await get_db_admin_ids()
    if not db_admins:
        await message.answer(
            "📋 Admin panel orqali qo'shilgan adminlar yo'q.\n"
            "(.env faylidagi doimiy adminlarni bu yerdan o'chirib bo'lmaydi.)"
        )
        return
    await message.answer(
        "📋 Admin panel orqali qo'shilgan adminlar ro'yxati:\n"
        "O'chirmoqchi bo'lganingizni tanlang:",
        reply_markup=admin_remove_list_buttons(db_admins),
    )


@router.callback_query(F.data.startswith("deladmin_"))
async def remove_admin_confirm(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    admin_id = int(call.data.replace("deladmin_", ""))
    await remove_admin(admin_id)
    await call.message.edit_text(f"✅ Admin <code>{admin_id}</code> o'chirildi.", parse_mode="HTML")
    await call.answer("O'chirildi!")


# ------------------------------------------------------------------
# Kino qo'shish (kategoriya bo'yicha)
# ------------------------------------------------------------------
@router.message(F.text.in_(set(ADMIN_ADD_BUTTONS.keys())), StateFilter(None))
async def add_movie_start(message: Message, state: FSMContext):
    if not await _admin_only(message):
        return
    category = ADMIN_ADD_BUTTONS[message.text]
    await state.update_data(category=category)
    await state.set_state(AddMovie.code)
    await message.answer(
        f"{message.text}\n\n"
        "🔢 Kino kodini kiriting, yoki avtomatik yaratish uchun \"avto\" deb yozing:"
    )


@router.message(AddMovie.code)
async def add_movie_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if code.lower() == "avto":
        code = await next_auto_code()

    existing = await get_movie_by_code(code)
    if existing:
        await message.answer("❌ Bu kod band. Boshqa kod kiriting:")
        return

    await state.update_data(code=code)
    await state.set_state(AddMovie.title)
    await message.answer(f"✅ Kod: {code}\n🎬 Kino nomini kiriting:")


@router.message(AddMovie.title)
async def add_movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddMovie.video)
    await message.answer("🎥 Endi kino video faylini yuboring:")


@router.message(AddMovie.video, F.video | F.document)
async def add_movie_video(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.video:
        file_id = message.video.file_id
    else:
        file_id = message.document.file_id

    await add_movie(
        code=data["code"],
        title=data["title"],
        category=data["category"],
        file_id=file_id,
        added_by=message.from_user.id,
    )
    await state.clear()

    category_label = CATEGORIES.get(data["category"], data["category"])
    await message.answer(
        f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📂 Bo'lim: {category_label}\n"
        f"🔢 Kod: <code>{data['code']}</code>\n"
        f"🎬 Nomi: {data['title']}",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )


@router.message(AddMovie.video)
async def add_movie_video_invalid(message: Message):
    await message.answer("⚠️ Iltimos, faqat video fayl (yoki video-hujjat) yuboring!")


# ------------------------------------------------------------------
# Kinolar ro'yxati — ko'rish / tahrirlash / o'chirish
# ------------------------------------------------------------------
@router.message(F.text == "📋 Kinolar ro'yxati", StateFilter(None))
async def movies_list_menu(message: Message):
    if not await _admin_only(message):
        return
    await message.answer(
        "📋 Qaysi bo'limdagi kinolarni ko'rmoqchisiz?",
        reply_markup=movie_category_filter_buttons(),
    )


@router.callback_query(F.data == "mlist_menu")
async def movies_list_menu_cb(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    await call.message.edit_text(
        "📋 Qaysi bo'limdagi kinolarni ko'rmoqchisiz?",
        reply_markup=movie_category_filter_buttons(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("mlist_"))
async def movies_list_page(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return

    # callback_data: mlist_<category|all>_<page>
    parts = call.data.split("_")
    page = int(parts[-1])
    category = "_".join(parts[1:-1])
    category = None if category == "all" else category

    total = await count_movies(category)
    offset = page * MOVIES_PAGE_SIZE
    movies = await list_movies(category, limit=MOVIES_PAGE_SIZE, offset=offset)

    if not movies:
        await call.message.edit_text(
            "📭 Bu bo'limda hozircha kino yo'q.",
            reply_markup=movie_category_filter_buttons(),
        )
        await call.answer()
        return

    has_more = (offset + MOVIES_PAGE_SIZE) < total
    label = CATEGORIES.get(category, "📃 Barcha kinolar") if category else "📃 Barcha kinolar"
    cat_for_cb = category or "all"

    await call.message.edit_text(
        f"{label}\n\nJami: {total} ta kino. Ko'rish uchun tanlang:",
        reply_markup=movie_list_buttons(movies, cat_for_cb, page, has_more),
    )
    await call.answer()


@router.callback_query(F.data.startswith("mview_"))
async def movie_view_detail(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    code = call.data.replace("mview_", "")
    movie = await get_movie_by_code(code)
    if not movie:
        await call.answer("❌ Bu kino topilmadi (o'chirilgan bo'lishi mumkin).", show_alert=True)
        return

    category_label = CATEGORIES.get(movie["category"], movie["category"] or "—")
    text = (
        f"🎬 <b>{movie['title']}</b>\n\n"
        f"🔢 Kod: <code>{movie['code']}</code>\n"
        f"📂 Bo'lim: {category_label}\n"
        f"👁 Ko'rishlar soni: {movie['views']}"
    )
    await call.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=movie_detail_buttons(code, movie["category"] or "all", 0),
    )
    await call.answer()


@router.callback_query(F.data.startswith("medittitle_"))
async def movie_edit_title_start(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    code = call.data.replace("medittitle_", "")
    await state.update_data(code=code)
    await state.set_state(EditMovieTitle.value)
    await call.message.answer(f"✏️ <code>{code}</code> kodli kino uchun yangi nomni kiriting:", parse_mode="HTML")
    await call.answer()


@router.message(EditMovieTitle.value)
async def movie_edit_title_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_movie_title(data["code"], message.text)
    await state.clear()
    await message.answer(
        f"✅ <code>{data['code']}</code> kodli kinoning nomi yangilandi!",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )


@router.callback_query(F.data.startswith("meditvideo_"))
async def movie_edit_video_start(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    code = call.data.replace("meditvideo_", "")
    await state.update_data(code=code)
    await state.set_state(EditMovieVideo.value)
    await call.message.answer(f"🎥 <code>{code}</code> kodli kino uchun yangi video faylni yuboring:", parse_mode="HTML")
    await call.answer()


@router.message(EditMovieVideo.value, F.video | F.document)
async def movie_edit_video_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id if message.video else message.document.file_id
    await update_movie_video(data["code"], file_id)
    await state.clear()
    await message.answer(
        f"✅ <code>{data['code']}</code> kodli kinoning videosi yangilandi!",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )


@router.message(EditMovieVideo.value)
async def movie_edit_video_invalid(message: Message):
    await message.answer("⚠️ Iltimos, faqat video fayl (yoki video-hujjat) yuboring!")


@router.callback_query(F.data.startswith("mdel_"))
async def movie_delete_confirm(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    code = call.data.replace("mdel_", "")
    movie = await get_movie_by_code(code)
    if not movie:
        await call.answer("❌ Bu kino topilmadi.", show_alert=True)
        return
    await call.message.answer(
        f"⚠️ <b>{movie['title']}</b> (<code>{code}</code>) kinosini rostdan ham o'chirmoqchimisiz?",
        parse_mode="HTML",
        reply_markup=movie_delete_confirm_buttons(code, movie["category"] or "all", 0),
    )
    await call.answer()


@router.callback_query(F.data.startswith("mdelyes_"))
async def movie_delete_execute(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    code = call.data.replace("mdelyes_", "")
    await delete_movie(code)
    await call.message.edit_text(f"🗑 <code>{code}</code> kodli kino o'chirildi.", parse_mode="HTML")
    await call.answer("O'chirildi!")


# ------------------------------------------------------------------
# Promokod qo'shish
# ------------------------------------------------------------------
@router.message(F.text == "🎟 Promokod qo'shish", StateFilter(None))
async def create_promo_start(message: Message, state: FSMContext):
    if not await _admin_only(message):
        return
    await state.set_state(CreatePromo.code)
    await message.answer("🎟 Promo kod matnini kiriting (masalan: KINO2026):")


@router.message(CreatePromo.code)
async def create_promo_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await state.set_state(CreatePromo.days)
    await message.answer(
        f"⏳ Necha kunlik VIP bersin? (raqam kiriting, standart uchun \"-\" yozing — {PROMO_DEFAULT_DAYS} kun beriladi):"
    )


@router.message(CreatePromo.days)
async def create_promo_days(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        days = PROMO_DEFAULT_DAYS
    elif text.isdigit():
        days = int(text)
    else:
        await message.answer("❌ Faqat raqam kiriting yoki \"-\" yozing:")
        return

    await state.update_data(days=days)
    await state.set_state(CreatePromo.uses)
    await message.answer(
        f"👥 Nechta foydalanuvchi ishlata oladi? (raqam kiriting, standart uchun \"-\" — {PROMO_DEFAULT_USES} marta):"
    )


@router.message(CreatePromo.uses)
async def create_promo_uses(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        uses = PROMO_DEFAULT_USES
    elif text.isdigit() and int(text) > 0:
        uses = int(text)
    else:
        await message.answer("❌ Faqat musbat raqam kiriting yoki \"-\" yozing:")
        return

    data = await state.get_data()
    await create_promo(data["code"], data["days"], uses, message.from_user.id)
    await state.clear()

    await message.answer(
        f"✅ <b>Promo kod yaratildi!</b>\n\n"
        f"🎟 Kod: <code>{data['code']}</code>\n"
        f"⏳ Muddat: {data['days']} kun VIP\n"
        f"👥 Limit: {uses} marta ishlatiladi",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )


# ------------------------------------------------------------------
# Statistika
# ------------------------------------------------------------------
@router.message(F.text == "📊 Statistika", StateFilter(None))
async def statistics(message: Message):
    if not await _admin_only(message):
        return
    total_users, total_movies, total_vip = await get_stats()
    today_count = await users_joined_today()
    month_count = await users_joined_this_month()

    await message.answer(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"🆕 Bugun qo'shilganlar: <b>{today_count}</b>\n"
        f"📅 Shu oyda qo'shilganlar: <b>{month_count}</b>\n"
        f"💎 VIP a'zolar: <b>{total_vip}</b>\n"
        f"🎬 Jami kinolar: <b>{total_movies}</b>",
        parse_mode="HTML",
    )


# ------------------------------------------------------------------
# Tugma yaratish (custom reply-tugmalar)
# ------------------------------------------------------------------
@router.message(F.text == "🔘 Tugma yaratish", StateFilter(None))
async def create_button_start(message: Message, state: FSMContext):
    if not await _admin_only(message):
        return
    await state.set_state(CreateButton.text)
    await message.answer(
        "🔘 Yangi tugma matnini kiriting (foydalanuvchilarga shu matn bilan tugma chiqadi):\n"
        "Masalan: 📞 Aloqa"
    )


@router.message(CreateButton.text)
async def create_button_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text.strip())
    await state.set_state(CreateButton.response)
    await message.answer("💬 Bu tugma bosilganda bot nima deb javob bersin? Javob matnini kiriting:")


@router.message(CreateButton.response)
async def create_button_response(message: Message, state: FSMContext):
    data = await state.get_data()
    await create_custom_button(data["button_text"], message.text, message.from_user.id)
    await state.clear()

    await message.answer(
        f"✅ <b>Tugma yaratildi!</b>\n\n"
        f"🔘 Matni: {data['button_text']}\n\n"
        f"Tugma foydalanuvchilarning asosiy menyusida ko'rinadi.",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )


@router.message(F.text == "📋 Mavjud tugmalar", StateFilter(None))
async def list_custom_buttons(message: Message):
    if not await _admin_only(message):
        return
    buttons = await get_custom_buttons()
    if not buttons:
        await message.answer("📋 Hali hech qanday maxsus tugma yaratilmagan.")
        return
    await message.answer(
        "📋 Mavjud maxsus tugmalar (o'chirish uchun bosing):",
        reply_markup=custom_buttons_manage_list(buttons),
    )


@router.callback_query(F.data.startswith("delbtn_"))
async def delete_button_confirm(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer()
        return
    btn_id = int(call.data.replace("delbtn_", ""))
    buttons = await get_custom_buttons()
    target = next((b for b in buttons if b["id"] == btn_id), None)
    if target:
        await delete_custom_button(target["button_text"])
        await call.message.edit_text(f"✅ \"{target['button_text']}\" tugmasi o'chirildi.")
    await call.answer("O'chirildi!")


# ------------------------------------------------------------------
# Foydalanuvchilarga xabar yuborish (broadcast)
# ------------------------------------------------------------------
@router.message(F.text == "📢 Xabar yuborish", StateFilter(None))
async def broadcast_start(message: Message, state: FSMContext):
    if not await _admin_only(message):
        return
    await state.set_state(Broadcast.content)
    await message.answer("📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni (matn/rasm/video/hujjat) yuboring:")


@router.message(Broadcast.content)
async def broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    user_ids = await all_user_ids()
    sent, failed = 0, 0

    status_msg = await message.answer(f"⏳ Yuborilmoqda... (0/{len(user_ids)})")

    for i, uid in enumerate(user_ids, start=1):
        try:
            await message.bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... ({i}/{len(user_ids)})")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await status_msg.edit_text(f"✅ Yuborildi: {sent} ta\n❌ Xato: {failed} ta")

# Eslatma: "⬅️ Bosh menyu" tugmasi handlers/start.py da global ishlaydi
# (admin panelda ham, oddiy menyuda ham), shuning uchun bu yerda qayta yozilmadi.
