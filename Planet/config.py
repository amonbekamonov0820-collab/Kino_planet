import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Loyihaning ildizida .env faylini yarating va "
        "unga BOT_TOKEN=... qatorini qo'shing."
    )

# .env faylidagi ADMIN_IDS — botning "doimiy" adminlari.
# Bular admin panel orqali o'chirib bo'lmaydi (xavfsizlik uchun).
_raw_admins = os.getenv("ADMIN_IDS", "")
PERMANENT_ADMIN_IDS = [int(a.strip()) for a in _raw_admins.split(",") if a.strip().isdigit()]

# ------------------------------------------------------------------
# Kino bo'limlari (kategoriyalar)
# key -> (tugma matni, ko'rsatiladigan nomi)
# ------------------------------------------------------------------
CATEGORIES = {
    "ujas": "👻 Ujas kinolar",
    "boevik": "💥 Boevik kinolar",
    "komediya": "😂 Komediya kinolar",
    "drama": "🎭 Dramalar",
    "ozbek": "🇺🇿 O'zbek kinolar",
}

# Admin panelda "... kino qo'shish" tugmalari qaysi kategoriyalarga mos kelishi
ADMIN_ADD_BUTTONS = {
    "👻 Ujas kino qo'shish": "ujas",
    "💥 Boevik kino qo'shish": "boevik",
    "😂 Komediya kino qo'shish": "komediya",
    "🎭 Drama kino qo'shish": "drama",
    "🇺🇿 O'zbek kino qo'shish": "ozbek",
}

# ------------------------------------------------------------------
# Coin / VIP sozlamalari
# ------------------------------------------------------------------
COIN_FOR_START = 1          # botga birinchi marta /start bergani uchun
COIN_FOR_WATCH = 5          # kinoni ochib ko'rgani uchun (bir kino uchun 1 marta)
COIN_FOR_REFERRAL = 50      # do'st taklif qilgani uchun

VIP_COIN_PRICE = 500        # shuncha coinga necha kunlik VIP olish mumkin
VIP_COIN_DAYS = 7

VIP_MONTHLY_PRICE_TEXT = "15,000 UZS"
VIP_MONTHLY_DAYS = 30

WHEEL_COOLDOWN_HOURS = 24
WHEEL_PRIZES = [
    {"type": "coin", "amount": 1, "label": "1 🪙 Coin"},
    {"type": "coin", "amount": 5, "label": "5 🪙 Coin"},
    {"type": "vip", "amount": 1, "label": "1 kunlik 💎 VIP"},
]

PROMO_DEFAULT_DAYS = 7      # "1 haftalik VIP" — standart promo kod muddati
PROMO_DEFAULT_USES = 1

DB_NAME = "kino_bot.db"
