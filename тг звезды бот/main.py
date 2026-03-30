#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот для покупки Telegram Stars и Premium через Fragment.com
Исправленная версия с обработкой None значений
"""

import asyncio
import logging
import sys
import re
import json
import sqlite3
import secrets
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Принудительная установка UTF-8 для консоли
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import aiohttp

# ========== ЭМОДЗИ ДЛЯ РАЗНЫХ ТИПОВ ==========
EMOJI = {
    "stars": "⭐",
    "premium": "👑",
    "premium_gold": "💎",
    "premium_platinum": "✨",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "money": "💰",
    "gift": "🎁",
    "cart": "🛒",
    "history": "📜",
    "settings": "⚙️",
    "admin": "📊",
    "user": "👤",
    "time": "⏰",
    "rocket": "🚀",
    "star": "🌟",
    "crown": "👑",
    "diamond": "💎",
    "sparkles": "✨",
    "fire": "🔥",
    "party": "🎉",
    "package": "📦",
    "id": "🆔",
    "wallet": "🏦",
    "promocode": "🎟️",
    "back": "«",
    "confirm": "✅",
    "cancel": "❌",
    "wait": "⏳",
    "check": "🔍",
    "chart": "📈",
}


# ========== ГЕНЕРАТОР ID ЗАКАЗА ==========
def generate_order_id() -> str:
    """Генерация уникального ID заказа"""
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ0123456789', k=6))
    return f"FRG-{date_part}-{random_part}"


# ========== БЕЗОПАСНОЕ ФОРМАТИРОВАНИЕ ==========
def safe_format(value: Any, format_spec: str = ".4f") -> str:
    """Безопасное форматирование чисел с проверкой на None"""
    if value is None:
        return "0.0000"
    try:
        if isinstance(value, (int, float)):
            return format(value, format_spec)
        return str(value)
    except (ValueError, TypeError):
        return str(value) if value else "0.0000"


def safe_str(value: Any) -> str:
    """Безопасное преобразование в строку"""
    if value is None:
        return ""
    return str(value)


# ========== НАСТРОЙКА ==========
# Получите токен у @BotFather
BOT_TOKEN = "7867924002:AAE_Qf-PV9majqO_v_svflixeQZKEzswAcQ"

# Данные Fragment (получите по инструкции ниже)
SEED_PHRASE = "concert rude brisk slam supply critic inmate hub away farm cheese there green fortune divide laugh joy toddler super put deposit tell atom federal"
TONAPI_KEY = "AGSYKDWOUNFDUNAAAAAJ36FULVZES5ZLQKQ7PSPMCZZ7BUYJ4FTNQLRPTI4Y3WA6O6NLH2Y"

# Cookies Fragment (4 ключа)
FRAGMENT_COOKIES = {
    "stel_ssid": "1f5d571d9640e7d909_7948737683376495909",
    "stel_dt": "-180",
    "stel_token": "271bb5ba9d843c1f4eafd607aa7eddf2271bb5a0271bb6ba331465a0c688869a9f98d",
    "stel_ton_token": "wnqN-yK3T0K4fpNz1FHWtSmVQC0wiA9D5-EHHsY4xDIs_tYJHRShdEqCnBLxCiVSJAoovtGs1KfS4cnBv7HtLw-WdkghIFeABzTxY1d4LBc2h_GZFCwKu9Br02RjFiRE916jXHXytjvq5eYaMk2fvpUFjdoDhRNd55d13o6Qx4Q82JsxG3BhnOAwUP11J54Rhjt3cbUn",
}

# Настройки
ADMIN_IDS = [8429942952]  # ID администраторов

# Платежные системы (опционально)
CRYPTOBOT_TOKEN = ""
LOLZTEAM_TOKEN = ""
CRYSTALPAY_TOKEN = ""



# Режимы работы
TEST_MODE = False
MAINTENANCE_MODE = False

# Цены (в TON)
STARS_PRICES = {
    100: 0.15,
    500: 0.75,
    1000: 1.5,
    5000: 7.5,
    10000: 15.0,
    "custom": 0.0015
}

PREMIUM_PRICES = {
    3: 4.5,
    6: 9.0,
    12: 18.0
}

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ========== БАЗА ДАННЫХ ==========
class Database:
    """Класс для работы с SQLite базой данных"""

    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance REAL DEFAULT 0,
                    total_spent REAL DEFAULT 0,
                    total_stars INTEGER DEFAULT 0,
                    total_premium_months INTEGER DEFAULT 0,
                    is_blocked INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица покупок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    user_id INTEGER,
                    type TEXT,
                    amount INTEGER,
                    recipient TEXT,
                    price REAL,
                    currency TEXT DEFAULT 'TON',
                    transaction_id TEXT,
                    status TEXT DEFAULT 'pending',
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Таблица промокодов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promocodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    discount_type TEXT,
                    discount_value REAL,
                    max_uses INTEGER,
                    used_count INTEGER DEFAULT 0,
                    expires_at TIMESTAMP,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица платежных заявок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    currency TEXT,
                    payment_system TEXT,
                    payment_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Таблица настроек
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица рассылок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT,
                    total_sent INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица логов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Добавляем админа
            for admin_id in ADMIN_IDS:
                cursor.execute("""
                    INSERT OR IGNORE INTO users (user_id, is_admin) 
                    VALUES (?, 1)
                """, (admin_id,))

            conn.commit()

    # ========== USER METHODS ==========
    def get_user(self, user_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    def create_user(self, user_id: int, username: str = None, first_name: str = None,
                    last_name: str = None, referrer_id: int = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, referrer_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, referrer_id))
            conn.commit()

    def update_balance(self, user_id: int, amount: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET balance = balance + ?, total_spent = total_spent + ? 
                WHERE user_id = ?
            """, (amount, amount, user_id))
            conn.commit()

    def update_user_stats(self, user_id: int, stars: int = 0, premium_months: int = 0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET total_stars = total_stars + ?, total_premium_months = total_premium_months + ?
                WHERE user_id = ?
            """, (stars, premium_months, user_id))
            conn.commit()

    def update_last_active(self, user_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    def block_user(self, user_id: int, block: bool = True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (1 if block else 0, user_id))
            conn.commit()

    # ========== PURCHASE METHODS ==========
    def add_purchase(self, user_id: int, p_type: str, amount: int, recipient: str,
                     price: float, transaction_id: str, status: str = "completed") -> Dict:
        """Добавляет покупку и возвращает order_id"""
        order_id = generate_order_id()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO purchases (order_id, user_id, type, amount, recipient, price, transaction_id, status, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_id, user_id, p_type, amount, recipient, price, transaction_id, status,
                  datetime.now().isoformat() if status == "completed" else None))
            conn.commit()
            return {"order_id": order_id, "id": cursor.lastrowid}

    def get_purchase_by_order_id(self, order_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM purchases WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    def get_user_purchases(self, user_id: int, limit: int = 10) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM purchases 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def update_purchase_status(self, purchase_id: int, status: str, error: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE purchases 
                SET status = ?, error = ?, completed_at = ?
                WHERE id = ?
            """, (status, error, datetime.now().isoformat() if status == "completed" else None, purchase_id))
            conn.commit()

    # ========== PROMOCODE METHODS ==========
    def generate_promocode(self, length: int = 8) -> str:
        return secrets.token_hex(length // 2).upper()

    def create_promocode(self, code: str, discount_type: str, discount_value: float,
                         max_uses: int, expires_days: int, created_by: int) -> bool:
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO promocodes (code, discount_type, discount_value, max_uses, expires_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (code.upper(), discount_type, discount_value, max_uses, expires_at, created_by))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_promocode(self, code: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM promocodes WHERE code = ?", (code.upper(),))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    def use_promocode(self, code: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE promocodes 
                SET used_count = used_count + 1 
                WHERE code = ? AND used_count < max_uses
            """, (code.upper(),))
            conn.commit()
            return cursor.rowcount > 0

    def validate_promocode(self, code: str) -> Dict:
        promo = self.get_promocode(code)
        if not promo:
            return {"valid": False, "error": f"{EMOJI['error']} Промокод не найден"}

        if promo["used_count"] >= promo["max_uses"]:
            return {"valid": False, "error": f"{EMOJI['error']} Промокод уже использован"}

        if promo["expires_at"] and datetime.fromisoformat(promo["expires_at"]) < datetime.now():
            return {"valid": False, "error": f"{EMOJI['warning']} Срок действия промокода истек"}

        return {
            "valid": True,
            "discount_type": promo["discount_type"],
            "discount_value": promo["discount_value"]
        }

    def apply_discount(self, price: float, discount_type: str, discount_value: float) -> float:
        if discount_type == "percent":
            return price * (1 - discount_value / 100)
        elif discount_type == "fixed":
            return max(0, price - discount_value)
        return price

    # ========== PAYMENT METHODS ==========
    def add_payment(self, user_id: int, amount: float, currency: str,
                    payment_system: str, payment_id: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO payments (user_id, amount, currency, payment_system, payment_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, amount, currency, payment_system, payment_id))
            conn.commit()
            return cursor.lastrowid

    def complete_payment(self, payment_id: str, status: str = "completed"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE payments 
                SET status = ?, completed_at = CURRENT_TIMESTAMP 
                WHERE payment_id = ?
            """, (status, payment_id))
            conn.commit()

    # ========== STATISTICS METHODS ==========
    def get_stats(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
            blocked_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM purchases WHERE status = 'completed'")
            total_purchases = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(price) FROM purchases WHERE status = 'completed'")
            total_volume = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(total_stars) FROM users")
            total_stars_sold = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(total_premium_months) FROM users")
            total_premium_sold = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_active > datetime('now', '-7 days')
            """)
            active_users = cursor.fetchone()[0]

            return {
                "total_users": total_users,
                "blocked_users": blocked_users,
                "active_users": active_users,
                "total_purchases": total_purchases,
                "total_volume": total_volume,
                "total_stars_sold": total_stars_sold,
                "total_premium_sold": total_premium_sold
            }

    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date(created_at) as date, 
                       COUNT(*) as purchases,
                       SUM(price) as volume
                FROM purchases 
                WHERE status = 'completed' 
                AND created_at > datetime('now', ?)
                GROUP BY date(created_at)
                ORDER BY date DESC
            """, (f'-{days} days',))
            rows = cursor.fetchall()
            return [{"date": row[0], "purchases": row[1], "volume": row[2] or 0} for row in rows]

    # ========== BROADCAST METHODS ==========
    def add_broadcast(self, message: str, created_by: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO broadcasts (message, created_by)
                VALUES (?, ?)
            """, (message, created_by))
            conn.commit()
            return cursor.lastrowid

    def update_broadcast_stats(self, broadcast_id: int, sent: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE broadcasts 
                SET total_sent = total_sent + ?, status = 'completed'
                WHERE id = ?
            """, (sent, broadcast_id))
            conn.commit()

    # ========== SETTINGS METHODS ==========
    def get_setting(self, key: str, default: str = None) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()

    # ========== LOG METHODS ==========
    def add_log(self, level: str, module: str, message: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logs (level, module, message)
                VALUES (?, ?, ?)
            """, (level, module, message[:500]))
            conn.commit()

    def get_logs(self, limit: int = 100) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM logs ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


db = Database()


# ========== FRAGMENT СЕРВИС ==========
class FragmentService:
    """Сервис для работы с Fragment API"""

    def __init__(self):
        self.client = None

    async def __aenter__(self):
        try:
            from pyfragment import FragmentClient
            self.client = FragmentClient(
                seed=SEED_PHRASE,
                api_key=TONAPI_KEY,
                cookies=FRAGMENT_COOKIES,
                wallet_version="V4R2"
            )
            await self.client.__aenter__()
            logger.info(f"{EMOJI['success']} Fragment клиент успешно инициализирован")
            return self
        except ImportError:
            raise Exception("pyfragment не установлен")
        except Exception as e:
            logger.error(f"{EMOJI['error']} Ошибка инициализации: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            try:
                await self.client.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.error(f"Ошибка закрытия: {e}")

    async def buy_stars(self, username: str, amount: int) -> Dict[str, Any]:
        if TEST_MODE:
            logger.info(f"{EMOJI['stars']} [TEST] Покупка Stars: {amount} для {username}")
            return {
                "success": True,
                "stars": amount,
                "username": username.replace("@", ""),
                "transaction_id": f"test_{int(datetime.now().timestamp())}"
            }

        try:
            if username.startswith("@"):
                username = username[1:]

            logger.info(f"{EMOJI['stars']} Покупка Stars: {amount} для @{username}")

            result = await self.client.purchase_stars(
                username=f"@{username}",
                amount=amount,
                show_sender=False
            )

            return {
                "success": True,
                "stars": amount,
                "username": username,
                "transaction_id": getattr(result, 'transaction_id', 'unknown')
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"{EMOJI['error']} Ошибка покупки Stars: {error_msg}")
            db.add_log("ERROR", "fragment", f"buy_stars: {error_msg[:200]}")

            if "Insufficient" in error_msg:
                return {"success": False, "error": f"{EMOJI['money']} Недостаточно средств на TON кошельке"}
            elif "User not found" in error_msg:
                return {"success": False, "error": f"{EMOJI['error']} Пользователь не найден в Telegram"}
            elif "cookies" in error_msg.lower():
                return {"success": False, "error": f"{EMOJI['warning']} Ошибка авторизации. Обновите cookies Fragment"}
            else:
                return {"success": False, "error": f"{EMOJI['error']} Ошибка: {error_msg[:150]}"}

    async def buy_premium(self, username: str, months: int) -> Dict[str, Any]:
        if TEST_MODE:
            logger.info(f"{EMOJI['premium']} [TEST] Покупка Premium: {months} мес. для {username}")
            return {
                "success": True,
                "months": months,
                "username": username.replace("@", ""),
                "transaction_id": f"test_{int(datetime.now().timestamp())}"
            }

        try:
            if username.startswith("@"):
                username = username[1:]

            logger.info(f"{EMOJI['premium']} Покупка Premium: {months} мес. для @{username}")

            result = await self.client.purchase_premium(
                username=f"@{username}",
                months=months,
                show_sender=False
            )

            return {
                "success": True,
                "months": months,
                "username": username,
                "transaction_id": getattr(result, 'transaction_id', 'unknown')
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"{EMOJI['error']} Ошибка покупки Premium: {error_msg}")
            db.add_log("ERROR", "fragment", f"buy_premium: {error_msg[:200]}")

            if "Insufficient" in error_msg:
                return {"success": False, "error": f"{EMOJI['money']} Недостаточно средств на TON кошельке"}
            elif "User not found" in error_msg:
                return {"success": False, "error": f"{EMOJI['error']} Пользователь не найден в Telegram"}
            elif "cookies" in error_msg.lower():
                return {"success": False, "error": f"{EMOJI['warning']} Ошибка авторизации. Обновите cookies Fragment"}
            else:
                return {"success": False, "error": f"{EMOJI['error']} Ошибка: {error_msg[:150]}"}


# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{EMOJI['stars']} Купить Stars", callback_data="buy_stars"),
            InlineKeyboardButton(text=f"{EMOJI['premium']} Купить Premium", callback_data="buy_premium"),
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['promocode']} Промокод", callback_data="promocode"),
            InlineKeyboardButton(text=f"{EMOJI['money']} Пополнить", callback_data="deposit"),
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['history']} История", callback_data="history"),
            InlineKeyboardButton(text=f"{EMOJI['info']} Помощь", callback_data="help"),
        ],
    ])


def get_stars_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"100 {EMOJI['stars']} (0.15 TON)", callback_data="stars_100"),
            InlineKeyboardButton(text=f"500 {EMOJI['stars']} (0.75 TON)", callback_data="stars_500"),
        ],
        [
            InlineKeyboardButton(text=f"1000 {EMOJI['stars']} (1.5 TON)", callback_data="stars_1000"),
            InlineKeyboardButton(text=f"5000 {EMOJI['stars']} (7.5 TON)", callback_data="stars_5000"),
        ],
        [
            InlineKeyboardButton(text=f"10000 {EMOJI['stars']} (15 TON)", callback_data="stars_10000"),
            InlineKeyboardButton(text=f"{EMOJI['sparkles']} Свое число", callback_data="stars_custom"),
        ],
        [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")],
    ])


def get_premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"3 {EMOJI['crown']} ({PREMIUM_PRICES[3]} TON)", callback_data="premium_3"),
            InlineKeyboardButton(text=f"6 {EMOJI['crown']} ({PREMIUM_PRICES[6]} TON)", callback_data="premium_6"),
        ],
        [
            InlineKeyboardButton(text=f"12 {EMOJI['crown']} ({PREMIUM_PRICES[12]} TON)", callback_data="premium_12"),
        ],
        [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")],
    ])


def get_confirm_keyboard(item_type: str, promocode_applied: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=f"{EMOJI['confirm']} Подтвердить", callback_data=f"confirm_{item_type}"),
            InlineKeyboardButton(text=f"{EMOJI['cancel']} Отмена", callback_data="cancel_purchase"),
        ],
    ]
    if not promocode_applied:
        buttons.insert(0, [InlineKeyboardButton(text=f"{EMOJI['promocode']} Применить промокод",
                                                callback_data="apply_promocode")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")]
    ])


# ========== СОСТОЯНИЯ FSM ==========
class PurchaseState(StatesGroup):
    waiting_for_username = State()
    waiting_for_stars_amount = State()
    waiting_for_premium_months = State()
    waiting_for_confirmation = State()
    waiting_for_custom_stars = State()
    waiting_for_promocode = State()


# ========== ОБРАБОТЧИКИ ==========
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])

    user = db.get_user(message.from_user.id)
    if not user:
        db.create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
            referrer_id if referrer_id != message.from_user.id else None
        )

    db.update_last_active(message.from_user.id)

    maintenance = db.get_setting("maintenance_mode", "False") == "True"
    if maintenance and message.from_user.id not in ADMIN_IDS:
        await message.answer(
            f"{EMOJI['warning']} <b>Бот на техническом обслуживании</b>\n\n"
            "Пожалуйста, зайдите позже.",
            reply_markup=get_back_keyboard()
        )
        return

    await message.answer(
        f"{EMOJI['rocket']} <b>Добро пожаловать в Fragment Bot!</b> {EMOJI['rocket']}\n\n"
        "Я помогу вам купить Telegram Stars и Premium через Fragment.com\n\n"
        f"{EMOJI['stars']} <b>Stars</b> — внутренняя валюта Telegram\n"
        f"{EMOJI['premium']} <b>Premium</b> — расширенные возможности\n\n"
        f"{'🧪 <b>ТЕСТОВЫЙ РЕЖИМ ВКЛЮЧЕН</b>\n\n' if TEST_MODE else ''}"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        f"{EMOJI['info']} <b>Помощь по боту</b>\n\n"
        f"<b>{EMOJI['package']} Доступные товары:</b>\n"
        f"{EMOJI['stars']} Telegram Stars — 100-10000 шт.\n"
        f"{EMOJI['premium']} Telegram Premium — 3/6/12 месяцев\n\n"
        f"<b>{EMOJI['cart']} Как купить:</b>\n"
        f"1️⃣ Нажмите «Купить Stars» или «Купить Premium»\n"
        f"2️⃣ Введите username получателя\n"
        f"3️⃣ Выберите количество\n"
        f"4️⃣ При желании примените промокод\n"
        f"5️⃣ Подтвердите покупку\n\n"
        f"<b>{EMOJI['money']} Цены:</b>\n"
        f"Stars: 100⭐ = 0.15 TON, 1000⭐ = 1.5 TON\n"
        f"Premium: 3 мес = 4.5 TON, 12 мес = 18 TON\n\n"
        f"<b>{EMOJI['promocode']} Промокоды:</b>\n"
        f"Введите /promocode или нажмите кнопку\n\n"
        f"<b>{EMOJI['history']} История:</b>\n"
        f"Нажмите «История» для просмотра покупок с ID заказов\n\n"
        f"📞 По вопросам: @fragment_support",
        reply_markup=get_back_keyboard()
    )


@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user = db.get_user(message.from_user.id)
    balance = user.get("balance", 0) if user else 0

    await message.answer(
        f"{EMOJI['money']} <b>Ваш баланс</b>\n\n"
        f"<code>{safe_format(balance)} TON</code>\n\n"
        f"<b>Как пополнить:</b>\n"
        f"• Нажмите «Пополнить»\n"
        f"• Выберите платежную систему\n"
        f"• Оплатите счет\n"
        f"• Баланс пополнится автоматически\n\n"
        f"<b>Комиссия сети:</b> ≈0.05 TON",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJI['money']} Пополнить", callback_data="deposit")],
            [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")]
        ])
    )


@dp.message(Command("promocode"))
async def cmd_promocode(message: Message, state: FSMContext):
    await state.set_state(PurchaseState.waiting_for_promocode)
    await message.answer(
        f"{EMOJI['promocode']} <b>Активация промокода</b>\n\n"
        "Введите промокод для активации скидки.\n\n"
        "Для отмены введите /cancel",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        f"{EMOJI['rocket']} <b>Главное меню</b> {EMOJI['rocket']}\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)


@dp.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    await callback.answer()
    await cmd_balance(callback.message)


@dp.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery):
    await callback.answer()

    purchases = db.get_user_purchases(callback.from_user.id, limit=10)

    if not purchases:
        await callback.message.edit_text(
            f"{EMOJI['history']} <b>История покупок</b>\n\n"
            "У вас пока нет покупок.",
            reply_markup=get_back_keyboard()
        )
        return

    text = f"{EMOJI['history']} <b>История покупок</b>\n\n"
    for p in purchases:
        emoji_item = EMOJI['stars'] if p["type"] == "stars" else EMOJI['premium']
        date = safe_str(p["created_at"])[:10] if p.get("created_at") else "?"
        status_emoji = EMOJI['success'] if p.get("status") == "completed" else EMOJI['wait']
        price = safe_format(p.get("price", 0))
        order_id = safe_str(p.get("order_id", "N/A"))
        amount = p.get("amount", 0)
        recipient = safe_str(p.get("recipient", "unknown"))

        text += f"{emoji_item} <b>Заказ #{order_id}</b>\n"
        text += f"   {p['type'].title()} | {amount} | @{recipient}\n"
        text += f"   {status_emoji} {price} TON | {date}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "promocode")
async def callback_promocode(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_promocode)
    await callback.message.edit_text(
        f"{EMOJI['promocode']} <b>Активация промокода</b>\n\n"
        "Введите промокод для активации скидки.\n\n"
        "Для отмены нажмите «Назад»",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "buy_stars")
async def callback_buy_stars(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_username)
    await state.update_data(purchase_type="stars")
    await callback.message.edit_text(
        f"{EMOJI['stars']} <b>Покупка Telegram Stars</b>\n\n"
        "Введите username получателя.\n"
        "Формат: @username или просто username\n\n"
        "<b>Пример:</b> @durov или durov\n\n"
        "Для отмены введите /cancel",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "buy_premium")
async def callback_buy_premium(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_username)
    await state.update_data(purchase_type="premium")
    await callback.message.edit_text(
        f"{EMOJI['premium']} <b>Покупка Telegram Premium</b>\n\n"
        "Введите username получателя.\n"
        "Формат: @username или просто username\n\n"
        "<b>Пример:</b> @durov или durov\n\n"
        "Для отмены введите /cancel",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "stars_custom")
async def callback_stars_custom(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_custom_stars)
    await callback.message.edit_text(
        f"{EMOJI['stars']} <b>Произвольное количество Stars</b>\n\n"
        "Введите количество Stars (от 1 до 100000).\n\n"
        "Цена: 1 Star = 0.0015 TON\n\n"
        "Для отмены введите /cancel",
        reply_markup=get_back_keyboard()
    )


@dp.message(PurchaseState.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    username_raw = message.text.strip()
    username = username_raw.replace("@", "")

    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
        await message.answer(
            f"{EMOJI['error']} <b>Некорректный username</b>\n\n"
            "Username должен содержать:\n"
            "• Латинские буквы (a-z, A-Z)\n"
            "• Цифры (0-9)\n"
            "• Нижнее подчеркивание (_)\n"
            "• Длину 5-32 символов\n\n"
            "Попробуйте еще раз:",
            reply_markup=get_back_keyboard()
        )
        return

    data = await state.get_data()
    purchase_type = data.get("purchase_type")

    await state.update_data(username=username)

    if purchase_type == "stars":
        await state.set_state(PurchaseState.waiting_for_stars_amount)
        await message.answer(
            f"{EMOJI['user']} <b>Получатель:</b> @{username}\n\n"
            "Выберите количество Stars:",
            reply_markup=get_stars_keyboard()
        )
    else:
        await state.set_state(PurchaseState.waiting_for_premium_months)
        await message.answer(
            f"{EMOJI['user']} <b>Получатель:</b> @{username}\n\n"
            "Выберите срок подписки Premium:",
            reply_markup=get_premium_keyboard()
        )


@dp.message(PurchaseState.waiting_for_custom_stars)
async def process_custom_stars(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount < 1 or amount > 100000:
            raise ValueError
    except ValueError:
        await message.answer(
            f"{EMOJI['error']} <b>Некорректное количество</b>\n\n"
            "Введите число от 1 до 100000.",
            reply_markup=get_back_keyboard()
        )
        return

    data = await state.get_data()
    username = data.get("username")

    await state.update_data(stars_amount=amount)
    await state.update_data(item_type="stars")
    await state.update_data(item_amount=amount)
    await state.set_state(PurchaseState.waiting_for_confirmation)

    price = amount * STARS_PRICES["custom"]

    await message.answer(
        f"{EMOJI['cart']} <b>Подтверждение покупки</b>\n\n"
        f"{EMOJI['stars']} <b>Товар:</b> Telegram Stars\n"
        f"{EMOJI['user']} <b>Получатель:</b> @{username}\n"
        f"{EMOJI['package']} <b>Количество:</b> {amount} Stars\n"
        f"{EMOJI['money']} <b>Стоимость:</b> {safe_format(price)} TON\n\n"
        f"{EMOJI['confirm']} Подтвердите покупку:",
        reply_markup=get_confirm_keyboard("stars")
    )


@dp.message(PurchaseState.waiting_for_promocode)
async def process_promocode(message: Message, state: FSMContext):
    code = message.text.strip().upper()

    validation = db.validate_promocode(code)

    if not validation["valid"]:
        await message.answer(
            f"{validation['error']}\n\n"
            "Попробуйте другой промокод или нажмите «Назад»",
            reply_markup=get_back_keyboard()
        )
        return

    await state.update_data(promocode=code, discount=validation)

    data = await state.get_data()
    item_type = data.get("item_type")
    item_amount = data.get("item_amount")
    username = data.get("username")

    if item_type == "stars":
        price = item_amount * STARS_PRICES.get(item_amount, STARS_PRICES["custom"])
    else:
        price = PREMIUM_PRICES.get(item_amount, item_amount * 1.5)

    discounted_price = db.apply_discount(price, validation["discount_type"], validation["discount_value"])

    await state.update_data(price=discounted_price, original_price=price)

    emoji_item = EMOJI['stars'] if item_type == "stars" else EMOJI['premium']
    discount_value = validation['discount_value']
    discount_symbol = '%' if validation['discount_type'] == 'percent' else ' TON'

    await message.answer(
        f"{EMOJI['success']} <b>Промокод активирован!</b>\n\n"
        f"{EMOJI['promocode']} <b>Промокод:</b> {code}\n"
        f"{EMOJI['gift']} <b>Скидка:</b> {discount_value}{discount_symbol}\n\n"
        f"{EMOJI['cart']} <b>Подтверждение покупки</b>\n\n"
        f"{emoji_item} <b>Товар:</b> {'Stars' if item_type == 'stars' else 'Premium'}\n"
        f"{EMOJI['user']} <b>Получатель:</b> @{username}\n"
        f"{EMOJI['package']} <b>Количество:</b> {item_amount} {'⭐' if item_type == 'stars' else 'мес.'}\n"
        f"{EMOJI['money']} <b>Исходная цена:</b> {safe_format(price)} TON\n"
        f"{EMOJI['gift']} <b>Цена со скидкой:</b> {safe_format(discounted_price)} TON\n\n"
        f"{EMOJI['confirm']} Подтвердите покупку:",
        reply_markup=get_confirm_keyboard(item_type, promocode_applied=True)
    )

    await state.set_state(PurchaseState.waiting_for_confirmation)


@dp.callback_query(F.data.startswith("stars_"))
async def process_stars_amount(callback: CallbackQuery, state: FSMContext):
    if callback.data == "stars_custom":
        await callback_stars_custom(callback, state)
        return

    amount = int(callback.data.split("_")[1])
    data = await state.get_data()
    username = data.get("username")

    price = STARS_PRICES.get(amount, amount * STARS_PRICES["custom"])

    await state.update_data(
        stars_amount=amount,
        item_type="stars",
        item_amount=amount,
        price=price
    )
    await state.set_state(PurchaseState.waiting_for_confirmation)

    await callback.answer()
    await callback.message.edit_text(
        f"{EMOJI['cart']} <b>Подтверждение покупки</b>\n\n"
        f"{EMOJI['stars']} <b>Товар:</b> Telegram Stars\n"
        f"{EMOJI['user']} <b>Получатель:</b> @{username}\n"
        f"{EMOJI['package']} <b>Количество:</b> {amount} Stars\n"
        f"{EMOJI['money']} <b>Стоимость:</b> {safe_format(price)} TON\n\n"
        f"{EMOJI['confirm']} Подтвердите покупку:",
        reply_markup=get_confirm_keyboard("stars")
    )


@dp.callback_query(F.data.startswith("premium_"))
async def process_premium_months(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    data = await state.get_data()
    username = data.get("username")

    price = PREMIUM_PRICES.get(months, months * 1.5)

    await state.update_data(
        premium_months=months,
        item_type="premium",
        item_amount=months,
        price=price
    )
    await state.set_state(PurchaseState.waiting_for_confirmation)

    await callback.answer()
    await callback.message.edit_text(
        f"{EMOJI['cart']} <b>Подтверждение покупки</b>\n\n"
        f"{EMOJI['premium']} <b>Товар:</b> Telegram Premium\n"
        f"{EMOJI['user']} <b>Получатель:</b> @{username}\n"
        f"{EMOJI['crown']} <b>Срок:</b> {months} месяцев\n"
        f"{EMOJI['money']} <b>Стоимость:</b> {safe_format(price)} TON\n\n"
        f"{EMOJI['confirm']} Подтвердите покупку:",
        reply_markup=get_confirm_keyboard("premium")
    )


@dp.callback_query(F.data.startswith("confirm_"))
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer(f"{EMOJI['wait']} Обработка...")

    data = await state.get_data()
    username = data.get("username")
    item_type = data.get("item_type")
    item_amount = data.get("item_amount")
    price = data.get("price")
    promocode = data.get("promocode")

    if not item_type or not item_amount:
        await callback.message.edit_text(
            f"{EMOJI['error']} <b>Ошибка</b>\n\nСессия истекла. Начните заново.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    if promocode and not data.get("discount_applied"):
        validation = db.validate_promocode(promocode)
        if validation["valid"]:
            price = db.apply_discount(price, validation["discount_type"], validation["discount_value"])
            db.use_promocode(promocode)
            await state.update_data(discount_applied=True)

    emoji_item = EMOJI['stars'] if item_type == "stars" else EMOJI['premium']

    await callback.message.edit_text(
        f"{EMOJI['wait']} <b>Обработка покупки...</b>\n\n"
        "Транзакция отправляется в блокчейн TON.\n"
        "Пожалуйста, подождите..."
    )

    try:
        async with FragmentService() as fragment:
            if item_type == "stars":
                result = await fragment.buy_stars(username, item_amount)
            else:
                result = await fragment.buy_premium(username, item_amount)

        if result.get("success"):
            tx_id = result.get("transaction_id", "unknown")

            # Сохраняем покупку с ID заказа
            purchase = db.add_purchase(
                user_id=callback.from_user.id,
                p_type=item_type,
                amount=item_amount,
                recipient=username,
                price=price,
                transaction_id=tx_id
            )

            order_id = purchase["order_id"]

            # Обновляем статистику
            stars = item_amount if item_type == "stars" else 0
            premium_months = item_amount if item_type == "premium" else 0
            db.update_user_stats(callback.from_user.id, stars, premium_months)

            test_mode_msg = f"\n{EMOJI['warning']} <b>ТЕСТОВЫЙ РЕЖИМ</b> — средства не списаны" if TEST_MODE else ""

            await callback.message.edit_text(
                f"{EMOJI['success']} <b>Покупка успешно выполнена!</b>{test_mode_msg}\n\n"
                f"{EMOJI['id']} <b>ID заказа:</b> <code>{order_id}</code>\n"
                f"{emoji_item} <b>Товар:</b> {'Stars' if item_type == 'stars' else 'Premium'}\n"
                f"{EMOJI['user']} <b>Получатель:</b> @{username}\n"
                f"{EMOJI['package']} <b>Количество:</b> {item_amount} {'⭐' if item_type == 'stars' else 'мес.'}\n"
                f"{EMOJI['money']} <b>Сумма:</b> {safe_format(price)} TON\n"
                f"{EMOJI['id']} <b>TX ID:</b> <code>{tx_id[:20] if tx_id else 'N/A'}...</code>\n\n"
                f"{EMOJI['party']} <b>Статус:</b> Доставлено!\n\n"
                f"✨ Спасибо за использование бота!",
                reply_markup=get_main_keyboard()
            )

            # Уведомление админам
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"{EMOJI['cart']} <b>Новая покупка!</b>\n\n"
                        f"{EMOJI['id']} <b>Заказ:</b> <code>{order_id}</code>\n"
                        f"{EMOJI['user']} <b>Пользователь:</b> @{callback.from_user.username or 'unknown'}\n"
                        f"{emoji_item} <b>Товар:</b> {'Stars' if item_type == 'stars' else 'Premium'}\n"
                        f"{EMOJI['package']} <b>Кол-во:</b> {item_amount}\n"
                        f"{EMOJI['user']} <b>Получатель:</b> @{username}\n"
                        f"{EMOJI['money']} <b>Сумма:</b> {safe_format(price)} TON\n"
                        f"{EMOJI['id']} <b>TX:</b> <code>{tx_id[:30] if tx_id else 'N/A'}...</code>"
                    )
                except Exception as e:
                    logger.error(f"Ошибка уведомления админа: {e}")
        else:
            error_msg = result.get("error", "Неизвестная ошибка")
            await callback.message.edit_text(
                f"{EMOJI['error']} <b>Ошибка покупки</b>\n\n{error_msg}\n\n"
                f"<b>{EMOJI['warning']} Возможные причины:</b>\n"
                f"• Недостаточно TON на кошельке\n"
                f"• Неправильный username\n"
                f"• Проблемы с cookies Fragment\n"
                f"• Пользователь не зарегистрирован в Telegram\n\n"
                f"Попробуйте позже или обратитесь к администратору.",
                reply_markup=get_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        db.add_log("CRITICAL", "purchase", str(e)[:200])
        await callback.message.edit_text(
            f"{EMOJI['error']} <b>Критическая ошибка</b>\n\n"
            f"Причина: {str(e)[:200]}\n\n"
            f"<b>{EMOJI['check']} Проверьте:</b>\n"
            f"• Cookies Fragment (актуальны?)\n"
            f"• SEED фразу (верна?)\n"
            f"• Баланс кошелька\n\n"
            f"Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

    await state.clear()


@dp.callback_query(F.data == "apply_promocode")
async def callback_apply_promocode(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_promocode)
    await callback.message.edit_text(
        f"{EMOJI['promocode']} <b>Введите промокод</b>\n\n"
        "Введите промокод для получения скидки.\n\n"
        "Для отмены нажмите «Назад»",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "cancel_purchase")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer(f"{EMOJI['cancel']} Покупка отменена")
    await callback.message.edit_text(
        f"{EMOJI['cancel']} Покупка отменена.\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer(f"{EMOJI['cancel']} Операция отменена.", reply_markup=get_main_keyboard())
    else:
        await message.answer("Нет активных операций для отмены.", reply_markup=get_main_keyboard())


@dp.callback_query(F.data == "deposit")
async def callback_deposit(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        f"{EMOJI['money']} <b>Пополнение баланса</b>\n\n"
        "Выберите способ пополнения:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💎 CryptoBot (USDT)", callback_data="deposit_cryptobot"),
                InlineKeyboardButton(text="🔄 LolzTeam", callback_data="deposit_lolzteam"),
            ],
            [
                InlineKeyboardButton(text="💳 CrystalPay", callback_data="deposit_crystalpay"),
            ],
            [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")],
        ])
    )


@dp.callback_query(F.data.startswith("deposit_"))
async def process_deposit(callback: CallbackQuery):
    await callback.answer(f"{EMOJI['info']} Функция в разработке")
    await callback.message.edit_text(
        f"{EMOJI['warning']} <b>Функция пополнения в разработке</b>\n\n"
        "Пока вы можете пополнить баланс через:\n"
        f"• Binance, Bybit, OKX\n"
        f"• P2P обменники\n"
        f"• Криптообменники (BestChange)\n\n"
        f"{EMOJI['wallet']} <b>Адрес кошелька TON:</b>\n"
        f"<code>EQD...ваш_адрес</code>",
        reply_markup=get_back_keyboard()
    )


@dp.message()
async def handle_unknown(message: Message):
    await message.answer(
        f"{EMOJI['error']} Я не понимаю эту команду.\n"
        "Используйте кнопки меню или /help для помощи.",
        reply_markup=get_main_keyboard()
    )


# ========== ЗАПУСК БОТА ==========
async def main():
    print(f"{EMOJI['rocket']} Fragment Bot запускается...")

    if TEST_MODE:
        print(f"{EMOJI['warning']} ТЕСТОВЫЙ РЕЖИМ ВКЛЮЧЕН - реальные покупки не выполняются")
    else:
        print(f"{EMOJI['money']} РЕАЛЬНЫЙ РЕЖИМ - будут списываться средства с TON кошелька")

    try:
        from pyfragment import FragmentClient
        print(f"{EMOJI['success']} pyfragment установлен")
    except ImportError:
        print(f"{EMOJI['error']} pyfragment не установлен! Установите: pip install pyfragment")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())