import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db

from handlers import start, admin, movies, wheel, vip, custom_buttons


async def main():
    logging.basicConfig(level=logging.INFO)

    # Ma'lumotlar bazasini ishga tushirish
    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Routerlarni ulash.
    # MUHIM: custom_buttons.router eng oxirida ulanadi, chunki u har qanday
    # matnli xabarni "ushlab qolishi" mumkin (faqat boshqa hech narsa mos
    # kelmasa ishlaydi).
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(movies.router)
    dp.include_router(wheel.router)
    dp.include_router(vip.router)
    dp.include_router(custom_buttons.router)

    print("\n" + "=" * 40)
    print("🚀 BOT MUVAFFAQIYATLI ISHGA TUSHDI!")
    print("=" * 40 + "\n")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot to'xtatildi.")
