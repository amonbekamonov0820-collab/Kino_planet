from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import CATEGORIES
from database import get_custom_buttons, is_admin


async def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=CATEGORIES["ujas"]), KeyboardButton(text=CATEGORIES["boevik"])],
        [KeyboardButton(text=CATEGORIES["komediya"]), KeyboardButton(text=CATEGORIES["drama"])],
        [KeyboardButton(text="🎲 Tasodifiy kino"), KeyboardButton(text=CATEGORIES["ozbek"])],
        [KeyboardButton(text="🪙 Coin ishlash"), KeyboardButton(text="🎡 Omad g'ildiragi")],
        [KeyboardButton(text="👤 Profil"), KeyboardButton(text="💎 VIP obuna")],
    ]

    # Admin tomonidan yaratilgan qo'shimcha tugmalar (2 tadan qatorga)
    custom = await get_custom_buttons()
    row = []
    for btn in custom:
        row.append(KeyboardButton(text=btn["button_text"]))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    if await is_admin(user_id):
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_admin_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="➕ Admin qo'shish"), KeyboardButton(text="➖ Admin o'chirish")],
        [KeyboardButton(text="👻 Ujas kino qo'shish"), KeyboardButton(text="💥 Boevik kino qo'shish")],
        [KeyboardButton(text="😂 Komediya kino qo'shish"), KeyboardButton(text="🎭 Drama kino qo'shish")],
        [KeyboardButton(text="🇺🇿 O'zbek kino qo'shish")],
        [KeyboardButton(text="🎟 Promokod qo'shish"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📋 Kinolar ro'yxati")],
        [KeyboardButton(text="🔘 Tugma yaratish"), KeyboardButton(text="📋 Mavjud tugmalar")],
        [KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="⬅️ Bosh menyu")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
