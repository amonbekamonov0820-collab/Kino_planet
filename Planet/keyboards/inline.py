from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import VIP_MONTHLY_PRICE_TEXT, VIP_COIN_PRICE, VIP_COIN_DAYS


def movie_action_buttons(movie_code: str):
    buttons = [
        [InlineKeyboardButton(text="💬 Do'stga ulashish", switch_inline_query=f"kino_{movie_code}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscription_gate_buttons(missing_channels):
    buttons = []
    for ch in missing_channels:
        if ch["invite_link"]:
            link = ch["invite_link"]
        elif ch["username"]:
            link = f"https://t.me/{ch['username']}"
        else:
            link = None
        title = ch["title"] or "Kanal"
        if link:
            buttons.append([InlineKeyboardButton(text=f"➕ {title}", url=link)])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def forced_channels_manage_list(channels):
    buttons = [
        [InlineKeyboardButton(text=f"🗑 {c['title'] or c['chat_id']}", callback_data=f"delch_{c['chat_id']}")]
        for c in channels
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def vip_purchase_buttons():
    buttons = [
        [InlineKeyboardButton(
            text=f"💎 1 Oylik VIP - {VIP_MONTHLY_PRICE_TEXT}",
            callback_data="vip_buy_money",
        )],
        [InlineKeyboardButton(
            text=f"🪙 Coin evaziga VIP olish ({VIP_COIN_PRICE} coin = {VIP_COIN_DAYS} kun)",
            callback_data="vip_buy_coins",
        )],
        [InlineKeyboardButton(text="🎟 Promo kod", callback_data="vip_promo")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_remove_list_buttons(admin_ids: list):
    buttons = [
        [InlineKeyboardButton(text=f"🗑 {aid} ni o'chirish", callback_data=f"deladmin_{aid}")]
        for aid in admin_ids
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def custom_buttons_manage_list(buttons_rows):
    buttons = [
        [InlineKeyboardButton(text=f"🗑 {b['button_text']}", callback_data=f"delbtn_{b['id']}")]
        for b in buttons_rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def movie_category_filter_buttons():
    from config import CATEGORIES
    buttons = [[InlineKeyboardButton(text="📃 Barcha kinolar", callback_data="mlist_all_0")]]
    row = []
    for key, label in CATEGORIES.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"mlist_{key}_0"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def movie_list_buttons(movies, category: str, page: int, has_more: bool):
    buttons = [
        [InlineKeyboardButton(text=f"🔢{m['code']} — {m['title'][:30]}", callback_data=f"mview_{m['code']}")]
        for m in movies
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"mlist_{category}_{page-1}"))
    if has_more:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"mlist_{category}_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Bo'limlarga qaytish", callback_data="mlist_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def movie_detail_buttons(code: str, category: str, page: int):
    buttons = [
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"medittitle_{code}")],
        [InlineKeyboardButton(text="🎥 Videoni almashtirish", callback_data=f"meditvideo_{code}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"mdel_{code}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data=f"mlist_{category}_{page}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def movie_delete_confirm_buttons(code: str, category: str, page: int):
    buttons = [
        [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"mdelyes_{code}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"mview_{code}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
