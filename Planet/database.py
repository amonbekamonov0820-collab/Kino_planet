import datetime
import aiosqlite

from config import DB_NAME, PERMANENT_ADMIN_IDS

# ============================================================
# INIT
# ============================================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                coins INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_expire TEXT,
                streak INTEGER DEFAULT 1,
                referrals INTEGER DEFAULT 0,
                referred_by INTEGER,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT,
                last_wheel_spin TEXT
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                title TEXT,
                category TEXT,
                file_id TEXT,
                views INTEGER DEFAULT 0,
                added_at TEXT,
                added_by INTEGER
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS watched (
                user_id INTEGER,
                movie_code TEXT,
                watched_at TEXT,
                PRIMARY KEY (user_id, movie_code)
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at TEXT
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                vip_days INTEGER DEFAULT 7,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TEXT,
                active INTEGER DEFAULT 1
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_usage (
                code TEXT,
                user_id INTEGER,
                used_at TEXT,
                PRIMARY KEY (code, user_id)
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS custom_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                button_text TEXT UNIQUE,
                response_text TEXT,
                created_by INTEGER,
                created_at TEXT
            )
        ''')

        await db.commit()

    # Eski bazadagi 'movies' jadvalida ba'zi ustunlar bo'lmasligi mumkin
    # (masalan avvalgi versiyadan qolgan bo'lsa) — xavfsiz tekshirib qo'shamiz.
    await _ensure_columns()


async def _ensure_columns():
    """Eski bazalarda yetishmayotgan ustunlarni qo'shib qo'yadi (xatosiz migratsiya)."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("PRAGMA table_info(users)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        migrations = {
            "vip_expire": "ALTER TABLE users ADD COLUMN vip_expire TEXT",
            "referred_by": "ALTER TABLE users ADD COLUMN referred_by INTEGER",
            "joined_at": "ALTER TABLE users ADD COLUMN joined_at TEXT",
            "last_wheel_spin": "ALTER TABLE users ADD COLUMN last_wheel_spin TEXT",
        }
        for col, stmt in migrations.items():
            if col not in cols:
                await db.execute(stmt)

        async with db.execute("PRAGMA table_info(movies)") as cur:
            mcols = {row[1] for row in await cur.fetchall()}
        movie_migrations = {
            "category": "ALTER TABLE movies ADD COLUMN category TEXT",
            "added_at": "ALTER TABLE movies ADD COLUMN added_at TEXT",
            "added_by": "ALTER TABLE movies ADD COLUMN added_by INTEGER",
        }
        for col, stmt in movie_migrations.items():
            if col not in mcols:
                await db.execute(stmt)

        await db.commit()


def _now():
    return datetime.datetime.now().isoformat()


# ============================================================
# USERS
# ============================================================
async def add_user(user_id: int, username: str, full_name: str, referred_by: int = None):
    """Foydalanuvchini bazaga qo'shadi (agar mavjud bo'lmasa). True qaytarsa — yangi user."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)) as cur:
            existing = await cur.fetchone()
        if existing:
            # ma'lumotlarni yangilab qo'yamiz (username o'zgargan bo'lishi mumkin)
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                (username or "Yo'q", full_name or "Foydalanuvchi", user_id),
            )
            await db.commit()
            return False

        await db.execute('''
            INSERT INTO users (user_id, username, full_name, coins, referred_by, joined_at)
            VALUES (?, ?, ?, 0, ?, ?)
        ''', (user_id, username or "Yo'q", full_name or "Foydalanuvchi", referred_by, _now()))
        await db.commit()
        return True


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()


async def add_coins(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def spend_coins(user_id: int, amount: int) -> bool:
    """Agar yetarli coin bo'lsa ayiradi va True qaytaradi, aks holda False."""
    user = await get_user(user_id)
    if not user or user["coins"] < amount:
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (amount, user_id))
        await db.commit()
    return True


async def add_referral(referrer_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (referrer_id,))
        await db.commit()


async def grant_vip(user_id: int, days: int):
    user = await get_user(user_id)
    now = datetime.datetime.now()
    base = now
    if user and user["vip_expire"]:
        try:
            current_expire = datetime.datetime.fromisoformat(user["vip_expire"])
            if current_expire > now:
                base = current_expire
        except ValueError:
            pass
    new_expire = base + datetime.timedelta(days=days)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET is_vip=1, vip_expire=? WHERE user_id=?",
            (new_expire.isoformat(), user_id),
        )
        await db.commit()
    return new_expire


async def check_and_expire_vip(user_id: int):
    """VIP muddati tugagan bo'lsa is_vip=0 qiladi. Joriy holatni qaytaradi (bool)."""
    user = await get_user(user_id)
    if not user or not user["is_vip"]:
        return False
    if user["vip_expire"]:
        try:
            expire = datetime.datetime.fromisoformat(user["vip_expire"])
            if expire < datetime.datetime.now():
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE users SET is_vip=0 WHERE user_id=?", (user_id,))
                    await db.commit()
                return False
        except ValueError:
            return bool(user["is_vip"])
    return bool(user["is_vip"])


async def set_wheel_spin(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_wheel_spin=? WHERE user_id=?", (_now(), user_id))
        await db.commit()


async def all_user_ids():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned=0") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


# ============================================================
# MOVIES
# ============================================================
async def get_movie_by_code(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE code=?", (code,)) as cur:
            return await cur.fetchone()


async def add_movie(code: str, title: str, category: str, file_id: str, added_by: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO movies (code, title, category, file_id, views, added_at, added_by)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        ''', (code, title, category, file_id, _now(), added_by))
        await db.commit()


async def next_auto_code() -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT code FROM movies") as cur:
            rows = await cur.fetchall()
    max_code = 100
    for (code,) in rows:
        if code and code.isdigit():
            max_code = max(max_code, int(code))
    return str(max_code + 1)


async def list_movies(category: str = None, limit: int = 8, offset: int = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if category:
            query = (
                "SELECT * FROM movies WHERE category=? "
                "ORDER BY id DESC LIMIT ? OFFSET ?"
            )
            params = (category, limit, offset)
        else:
            query = "SELECT * FROM movies ORDER BY id DESC LIMIT ? OFFSET ?"
            params = (limit, offset)
        async with db.execute(query, params) as cur:
            return await cur.fetchall()


async def count_movies(category: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        if category:
            async with db.execute("SELECT COUNT(*) FROM movies WHERE category=?", (category,)) as cur:
                return (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM movies") as cur:
            return (await cur.fetchone())[0]


async def update_movie_title(code: str, new_title: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE movies SET title=? WHERE code=?", (new_title, code))
        await db.commit()


async def update_movie_video(code: str, file_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE movies SET file_id=? WHERE code=?", (file_id, code))
        await db.commit()


async def update_movie_category(code: str, category: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE movies SET category=? WHERE code=?", (category, code))
        await db.commit()


async def delete_movie(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM movies WHERE code=?", (code,))
        await db.commit()


async def random_movie(category: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if category:
            query = "SELECT * FROM movies WHERE category=? ORDER BY RANDOM() LIMIT 1"
            params = (category,)
        else:
            query = "SELECT * FROM movies ORDER BY RANDOM() LIMIT 1"
            params = ()
        async with db.execute(query, params) as cur:
            return await cur.fetchone()


async def increment_views(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
        await db.commit()


async def mark_watched(user_id: int, movie_code: str) -> bool:
    """Agar bu foydalanuvchi shu kinoni ilk marta ochayotgan bo'lsa True qaytaradi
    (ya'ni +coin berish kerak), aks holda False."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT 1 FROM watched WHERE user_id=? AND movie_code=?", (user_id, movie_code)
        ) as cur:
            already = await cur.fetchone()
        if already:
            return False
        await db.execute(
            "INSERT INTO watched (user_id, movie_code, watched_at) VALUES (?, ?, ?)",
            (user_id, movie_code, _now()),
        )
        await db.commit()
        return True


# ============================================================
# STATISTIKA
# ============================================================
async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM movies") as cur:
            total_movies = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_vip=1") as cur:
            total_vip = (await cur.fetchone())[0]
        return total_users, total_movies, total_vip


async def users_joined_today():
    today = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (f"{today}%",)
        ) as cur:
            return (await cur.fetchone())[0]


async def users_joined_this_month():
    month_prefix = datetime.date.today().strftime("%Y-%m")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (f"{month_prefix}%",)
        ) as cur:
            return (await cur.fetchone())[0]


# ============================================================
# ADMINLAR (dinamik, admin panel orqali qo'shiladi/o'chiriladi)
# ============================================================
async def get_db_admin_ids():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM admins") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_all_admin_ids():
    db_admins = await get_db_admin_ids()
    return list(set(PERMANENT_ADMIN_IDS) | set(db_admins))


async def is_admin(user_id: int) -> bool:
    if user_id in PERMANENT_ADMIN_IDS:
        return True
    db_admins = await get_db_admin_ids()
    return user_id in db_admins


async def add_admin(user_id: int, added_by: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
            (user_id, added_by, _now()),
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


# ============================================================
# PROMO KODLAR
# ============================================================
async def create_promo(code: str, vip_days: int, max_uses: int, created_by: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO promo_codes (code, vip_days, max_uses, used_count, created_by, created_at, active)
            VALUES (?, ?, ?, 0, ?, ?, 1)
        ''', (code, vip_days, max_uses, created_by, _now()))
        await db.commit()


async def get_promo(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes WHERE code=?", (code,)) as cur:
            return await cur.fetchone()


async def redeem_promo(code: str, user_id: int):
    """Promo kodni ishlatishga urinadi. (success: bool, message_or_days) qaytaradi."""
    promo = await get_promo(code)
    if not promo or not promo["active"]:
        return False, "notfound"
    if promo["used_count"] >= promo["max_uses"]:
        return False, "limit"

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT 1 FROM promo_usage WHERE code=? AND user_id=?", (code, user_id)
        ) as cur:
            used_before = await cur.fetchone()
        if used_before:
            return False, "already_used"

        await db.execute(
            "INSERT INTO promo_usage (code, user_id, used_at) VALUES (?, ?, ?)",
            (code, user_id, _now()),
        )
        await db.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE code=?", (code,))
        await db.commit()

    await grant_vip(user_id, promo["vip_days"])
    return True, promo["vip_days"]


async def list_promos():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes ORDER BY created_at DESC") as cur:
            return await cur.fetchall()


# ============================================================
# CUSTOM TUGMALAR
# ============================================================
async def create_custom_button(button_text: str, response_text: str, created_by: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO custom_buttons (button_text, response_text, created_by, created_at)
            VALUES (?, ?, ?, ?)
        ''', (button_text, response_text, created_by, _now()))
        await db.commit()


async def get_custom_buttons():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM custom_buttons ORDER BY id") as cur:
            return await cur.fetchall()


async def get_custom_button_response(button_text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT response_text FROM custom_buttons WHERE button_text=?", (button_text,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def delete_custom_button(button_text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM custom_buttons WHERE button_text=?", (button_text,))
        await db.commit()

# ============================================================
# MAJBURIY OBUNA (FORCED CHANNELS)
# ============================================================
async def add_forced_channel(chat_id, title: str, username: str, invite_link: str, added_by: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO forced_channels (chat_id, title, username, invite_link, added_by, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(chat_id), title, username, invite_link, added_by, _now()))
        await db.commit()


async def get_forced_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM forced_channels ORDER BY id") as cur:
            return await cur.fetchall()


async def remove_forced_channel(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM forced_channels WHERE chat_id=?", (str(chat_id),))
        await db.commit()