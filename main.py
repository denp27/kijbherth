#!/usr/bin/env python3
import asyncio
import logging
import signal
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, get_stats
from handlers import user, shop, tasks, admin, referral
from utils.payments import cryptobot_client, platega_client
from utils.fragment_client import fragment_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="balance", description="💰 Баланс"),
        BotCommand(command="admin", description="🔧 Админ панель"),
        BotCommand(command="myid", description="🆔 Узнать свой ID"),
    ]
    await bot.set_my_commands(commands)


async def send_startup_notification(bot: Bot, admin_ids: list):
    stats = get_stats()
    
    text = f"""🤖 <b>Бот успешно запущен!</b> 🤖

📊 <b>Статистика на момент запуска:</b>
👥 Пользователей: {stats['total_users']}
💰 Выручка: {stats['total_revenue']}₽
⭐ Продано Stars: {stats['total_stars_sold']}
💎 Продано Premium: {stats['total_premium_sold']}
👥 Реферальных выплат: {stats['total_referral_paid']}₽

🚀 Все системы готовы к работе!"""
    
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
            logger.info(f"Startup notification sent to admin {admin_id}")
        except Exception as e:
            logger.error(f"Error sending startup notification to admin {admin_id}: {e}")


async def main():
    init_db()
    logger.info("Database initialized")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    await cryptobot_client.init_client()
    await platega_client.init_client()
    await fragment_client.init_client()
    logger.info("Payment systems initialized")

    dp.include_router(user.router)
    dp.include_router(shop.router)
    dp.include_router(tasks.router)
    dp.include_router(admin.router)
    dp.include_router(referral.router)

    await set_commands(bot)

    await send_startup_notification(bot, ADMIN_IDS)

    logger.info("Bot started successfully!")

    def shutdown_handler(signum, frame):
        logger.info("Shutting down...")
        loop = asyncio.get_event_loop()
        loop.stop()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
