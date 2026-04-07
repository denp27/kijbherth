#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот для продажи Telegram Stars и Premium
С поддержкой премиум эмодзи, пополнением через Platega.io и CryptoBot
"""

import asyncio
import logging
import sys
import re
import sqlite3
import secrets
import random
import hashlib
import json
import aiohttp
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

# ========== НАСТРОЙКА ==========
BOT_TOKEN = ""

# Данные Fragment
SEED_PHRASE = ""
TONAPI_KEY = "Y"

FRAGMENT_COOKIES = {
    "stel_ssid": "",
    "stel_dt": "",
    "stel_token": "",
    "stel_ton_token": "",
}

# Настройки Platega.io
PLATEGA_API_KEY = "your_platega_api_key"
PLATEGA_MERCHANT_ID = "your_merchant_id"
PLATEGA_API_URL = "https://platega.io/api/v1/invoice/create"
PLATEGA_WEBHOOK_SECRET = "your_webhook_secret"

# Настройки CryptoBot
CRYPTOBOT_API_KEY = "your_cryptobot_api_key"
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api/createInvoice"

# Настройки
ADMIN_IDS = [8429942952]
TEST_MODE = False
MAINTENANCE_MODE = False

# Цены в рублях
STARS_PRICES_RUB = {
    100: 57.0,
    500: 285.0,
    1000: 570.0,
    5000: 2850.0,
    10000: 5700.0,
    "custom": 0.57
}

PREMIUM_PRICES_RUB = {
    3: 1710.0,
    6: 3420.0,
    12: 6840.0
}

# Курс RUB к TON
RUB_TO_TON_RATE = 0.00263

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

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ========== ЭМОДЗИ ==========
EMOJI = {
    "stars": "⭐",
    "premium": "👑",
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
    "party": "🎉",
    "package": "📦",
    "id": "🆔",
    "wallet": "🏦",
    "promocode": "🎟️",
    "back": "«",
    "confirm": "✅",
    "cancel": "❌",
    "wait": "⏳",
    "chart": "📈",
    "myself": "👤",
    "other": "🎁",
    "delete": "🗑️",
    "list": "📋",
    "users": "👥",
    "broadcast": "📢",
    "rub": "₽",
    "usdt": "💎",
    "platega": "💳",
    "cryptobot": "🤖",
    "update": "🔄"
}

# ========== ГЕНЕРАТОР ID ==========
def generate_order_id() -> str:
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ0123456789', k=6))
    return f"FRG-{date_part}-{random_part}"


def safe_format(value: Any, format_spec: str = ".2f") -> str:
    if value is None:
        return "0.00"
    try:
        if isinstance(value, (int, float)):
            return format(value, format_spec)
        return str(value)
    except:
        return str(value) if value else "0.00"


# ========== КЛАСС ДЛЯ ПОЛУЧЕНИЯ ID ЭМОДЗИ ==========
class EmojiIDDetector:
    _emoji_cache = {}
    
    @staticmethod
    def extract_emoji_from_text(text: str) -> Optional[str]:
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F1E0-\U0001F1FF"
            "]+",
            flags=re.UNICODE
        )
        emojis = emoji_pattern.findall(text)
        return emojis[0] if emojis else None
    
    @staticmethod
    async def get_emoji_id(emoji_char: str, chat_id: int) -> Dict[str, Any]:
        if emoji_char in EmojiIDDetector._emoji_cache:
            return {
                "success": True,
                "emoji_char": emoji_char,
                "emoji_id": EmojiIDDetector._emoji_cache[emoji_char],
                "from_cache": True
            }
        
        try:
            message = await bot.send_message(chat_id=chat_id, text=emoji_char, parse_mode=None)
            message_id = message.message_id
            await asyncio.sleep(0.5)
            
            api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMessage"
            params = {"chat_id": chat_id, "message_id": message_id}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    data = await response.json()
                    if data.get("ok"):
                        message_text = data["result"].get("text", "")
                        pattern = r'<tg-emoji emoji-id="([^"]+)"'
                        match = re.search(pattern, message_text)
                        if match:
                            emoji_id = match.group(1)
                            try:
                                await bot.delete_message(chat_id, message_id)
                            except:
                                pass
                            EmojiIDDetector._emoji_cache[emoji_char] = emoji_id
                            return {
                                "success": True,
                                "emoji_char": emoji_char,
                                "emoji_id": emoji_id,
                                "from_cache": False
                            }
            return {"success": False, "error": "Не удалось получить ID"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def create_tg_emoji_tag(emoji_char: str, emoji_id: str) -> str:
        return f'<tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji>'


async def get_premium_tag(chat_id: int = None) -> str:
    """Получить тег премиум эмодзи"""
    try:
        chat_id = chat_id or ADMIN_IDS[0]
        result = await EmojiIDDetector.get_emoji_id("👑", chat_id)
        if result["success"]:
            return EmojiIDDetector.create_tg_emoji_tag("👑", result["emoji_id"])
    except:
        pass
    return "👑"


async def replace_premium_emoji(text: str, chat_id: int) -> str:
    """Заменяет плейсхолдер {premium} на тег эмодзи"""
    if "{premium}" not in text:
        return text
    try:
        result = await EmojiIDDetector.get_emoji_id("👑", chat_id)
        if result["success"]:
            premium_tag = EmojiIDDetector.create_tg_emoji_tag("👑", result["emoji_id"])
            return text.replace("{premium}", premium_tag)
    except:
        pass
    return text.replace("{premium}", "👑")


# ========== FRAGMENT СЕРВИС ==========
class FragmentService:
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
            return self
        except ImportError:
            raise Exception("pyfragment не установлен")
        except Exception as e:
            raise e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            try:
                await self.client.__aexit__(exc_type, exc_val, exc_tb)
            except:
                pass

    async def buy_stars(self, username: str, amount: int) -> Dict[str, Any]:
        if TEST_MODE:
            return {"success": True, "stars": amount, "username": username, "transaction_id": f"test_{int(datetime.now().timestamp())}"}
        try:
            if username.startswith("@"):
                username = username[1:]
            result = await self.client.purchase_stars(username=f"@{username}", amount=amount, show_sender=False)
            return {"success": True, "stars": amount, "username": username, "transaction_id": getattr(result, 'transaction_id', 'unknown')}
        except Exception as e:
            error_msg = str(e)
            if "Insufficient" in error_msg:
                return {"success": False, "error": "Недостаточно средств на TON кошельке"}
            elif "User not found" in error_msg:
                return {"success": False, "error": "Пользователь не найден в Telegram"}
            else:
                return {"success": False, "error": f"Ошибка: {error_msg[:150]}"}

    async def buy_premium(self, username: str, months: int) -> Dict[str, Any]:
        if TEST_MODE:
            return {"success": True, "months": months, "username": username, "transaction_id": f"test_{int(datetime.now().timestamp())}"}
        try:
            if username.startswith("@"):
                username = username[1:]
            result = await self.client.purchase_premium(username=f"@{username}", months=months, show_sender=False)
            return {"success": True, "months": months, "username": username, "transaction_id": getattr(result, 'transaction_id', 'unknown')}
        except Exception as e:
            error_msg = str(e)
            if "Insufficient" in error_msg:
                return {"success": False, "error": "Недостаточно средств на TON кошельке"}
            elif "User not found" in error_msg:
                return {"success": False, "error": "Пользователь не найден в Telegram"}
            else:
                return {"success": False, "error": f"Ошибка: {error_msg[:150]}"}


# ========== ПЛАТЕЖНЫЕ СИСТЕМЫ ==========
class PlategaPayment:
    @staticmethod
    async def create_invoice(amount_rub: float, order_id: str, user_id: int) -> Dict[str, Any]:
        try:
            payment_id = f"PLG_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
            payload = {
                "merchant_id": PLATEGA_MERCHANT_ID,
                "amount": amount_rub,
                "currency": "RUB",
                "order_id": order_id,
                "payment_id": payment_id,
                "description": f"Пополнение баланса на {amount_rub:.2f} ₽",
                "success_url": f"https://t.me/{bot.username}?start=payment_success_{payment_id}",
                "fail_url": f"https://t.me/{bot.username}?start=payment_fail_{payment_id}",
                "customer": {"id": str(user_id)}
            }
            sign_data = f"{PLATEGA_MERCHANT_ID}:{amount_rub}:{order_id}:{PLATEGA_WEBHOOK_SECRET}"
            payload["sign"] = hashlib.md5(sign_data.encode()).hexdigest()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(PLATEGA_API_URL, json=payload, headers={"Content-Type": "application/json"}) as response:
                    result = await response.json()
                    if result.get("status") == "success":
                        return {"success": True, "payment_id": payment_id, "invoice_url": result.get("invoice_url"), "amount_rub": amount_rub}
                    return {"success": False, "error": result.get("error", "Ошибка создания счета")}
        except Exception as e:
            return {"success": False, "error": str(e)}


class CryptoBotPayment:
    @staticmethod
    async def create_invoice(amount_usdt: float, order_id: str, user_id: int) -> Dict[str, Any]:
        try:
            payment_id = f"CRYPTO_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
            payload = {
                "asset": "USDT",
                "amount": amount_usdt,
                "description": f"Пополнение баланса на {amount_usdt} USDT",
                "payload": order_id
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(CRYPTOBOT_API_URL, json=payload, headers={"Crypto-Pay-API-Token": CRYPTOBOT_API_KEY}) as response:
                    result = await response.json()
                    if result.get("ok"):
                        invoice = result.get("result", {})
                        return {"success": True, "payment_id": payment_id, "invoice_url": invoice.get("bot_invoice_url"), "amount_usdt": amount_usdt}
                    return {"success": False, "error": result.get("error", "Ошибка создания счета")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance_rub REAL DEFAULT 0,
                    total_spent_rub REAL DEFAULT 0,
                    total_stars INTEGER DEFAULT 0,
                    total_premium_months INTEGER DEFAULT 0,
                    is_blocked INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    user_id INTEGER,
                    type TEXT,
                    amount INTEGER,
                    recipient TEXT,
                    price_rub REAL,
                    transaction_id TEXT,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payment_id TEXT UNIQUE,
                    user_id INTEGER,
                    amount REAL,
                    currency TEXT,
                    payment_system TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            for admin_id in ADMIN_IDS:
                cursor.execute("INSERT OR IGNORE INTO users (user_id, is_admin) VALUES (?, 1)", (admin_id,))
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('welcome_text', '🚀 <b>Добро пожаловать в Fragment Bot!</b> 🚀\n\nЯ помогу вам купить Telegram Stars и Premium\n\n⭐ <b>Stars</b> — внутренняя валюта Telegram\n{{premium}} <b>Premium</b> — расширенные возможности\n\n💰 Все цены указаны в РУБЛЯХ\n\nВыберите действие:')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_deposit', '100')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('max_deposit', '100000')")
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, row))
                if user_dict.get("balance_rub") is None:
                    user_dict["balance_rub"] = 0
                return user_dict
            return None

    def create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)", 
                          (user_id, username, first_name, last_name))
            conn.commit()

    def update_balance(self, user_id: int, amount: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance_rub = balance_rub + ?, total_spent_rub = total_spent_rub + ? WHERE user_id = ?", 
                          (amount, amount, user_id))
            conn.commit()

    def deduct_balance(self, user_id: int, amount: float) -> bool:
        if amount <= 0:
            return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance_rub FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[0] >= amount:
                cursor.execute("UPDATE users SET balance_rub = balance_rub - ? WHERE user_id = ?", (amount, user_id))
                conn.commit()
                return True
            return False

    def update_user_stats(self, user_id: int, stars: int = 0, premium_months: int = 0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET total_stars = total_stars + ?, total_premium_months = total_premium_months + ? WHERE user_id = ?", 
                          (stars, premium_months, user_id))
            conn.commit()

    def update_last_active(self, user_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
            conn.commit()

    def block_user(self, user_id: int, block: bool = True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (1 if block else 0, user_id))
            conn.commit()

    def add_purchase(self, user_id: int, p_type: str, amount: int, recipient: str, price: float, tx_id: str) -> Dict:
        order_id = generate_order_id()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO purchases (order_id, user_id, type, amount, recipient, price_rub, transaction_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (order_id, user_id, p_type, amount, recipient, price, tx_id))
            conn.commit()
            return {"order_id": order_id}

    def get_user_purchases(self, user_id: int, limit: int = 10) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM purchases WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_all_purchases(self, limit: int = 100) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM purchases ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def add_payment(self, payment_id: str, user_id: int, amount: float, currency: str, payment_system: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO payments (payment_id, user_id, amount, currency, payment_system, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                          (payment_id, user_id, amount, currency, payment_system))
            conn.commit()
            return cursor.lastrowid

    def update_payment(self, payment_id: str, status: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE payments SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE payment_id = ?", (status, payment_id))
            conn.commit()

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    def generate_promocode(self, length: int = 8) -> str:
        return secrets.token_hex(length // 2).upper()

    def create_promocode(self, code: str, discount_type: str, discount_value: float, max_uses: int, expires_days: int, created_by: int) -> bool:
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat() if expires_days > 0 else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO promocodes (code, discount_type, discount_value, max_uses, expires_at, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                              (code.upper(), discount_type, discount_value, max_uses, expires_at, created_by))
                conn.commit()
                return True
            except:
                return False

    def get_all_promocodes(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM promocodes ORDER BY created_at DESC")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def delete_promocode(self, code: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM promocodes WHERE code = ?", (code.upper(),))
            conn.commit()
            return cursor.rowcount > 0

    def validate_promocode(self, code: str) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM promocodes WHERE code = ? AND used_count < max_uses AND (expires_at IS NULL OR expires_at > datetime('now'))", (code.upper(),))
            row = cursor.fetchone()
            if row:
                return {"valid": True, "discount_type": row[2], "discount_value": row[3]}
            return {"valid": False, "error": "Промокод недействителен"}

    def use_promocode(self, code: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code.upper(),))
            conn.commit()
            return cursor.rowcount > 0

    def apply_discount(self, price: float, discount_type: str, discount_value: float) -> float:
        if discount_type == "percent":
            return price * (1 - discount_value / 100)
        return max(0, price - discount_value)

    def get_setting(self, key: str, default: str = None) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (key, value))
            conn.commit()

    def get_welcome_text(self) -> str:
        return self.get_setting("welcome_text", "🚀 <b>Добро пожаловать!</b>")

    def set_welcome_text(self, text: str):
        self.set_setting("welcome_text", text)

    def get_min_deposit(self) -> float:
        return float(self.get_setting("min_deposit", "100"))

    def get_max_deposit(self) -> float:
        return float(self.get_setting("max_deposit", "100000"))

    def add_broadcast(self, message: str, created_by: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO broadcasts (message, created_by) VALUES (?, ?)", (message, created_by))
            conn.commit()
            return cursor.lastrowid

    def update_broadcast_stats(self, broadcast_id: int, sent: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE broadcasts SET total_sent = ?, status = 'completed' WHERE id = ?", (sent, broadcast_id))
            conn.commit()

    def get_all_users(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username FROM users WHERE is_blocked = 0")
            rows = cursor.fetchall()
            return [{"user_id": row[0], "username": row[1]} for row in rows]

    def get_stats(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(price_rub) FROM purchases")
            total_volume = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM purchases")
            total_purchases = cursor.fetchone()[0] or 0
            return {"total_users": total_users, "total_volume": total_volume, "total_purchases": total_purchases}

    def add_log(self, level: str, module: str, message: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO logs (level, module, message) VALUES (?, ?, ?)", (level, module, message[:500]))
            conn.commit()


db = Database()


# ========== КЛАВИАТУРЫ ==========
async def get_main_keyboard() -> InlineKeyboardMarkup:
    premium_tag = await get_premium_tag()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Купить Stars", callback_data="buy_stars"),
         InlineKeyboardButton(text=f"{premium_tag} Купить Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🎟️ Промокод", callback_data="promocode"),
         InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="📜 История", callback_data="history"),
         InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit_menu")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
    ])


def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton(text="🎟️ Промокоды", callback_data="admin_promocodes")],
        [InlineKeyboardButton(text="📦 Все покупки", callback_data="admin_purchases"),
         InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
         InlineKeyboardButton(text="🔄 Обновить эмодзи", callback_data="admin_update_emoji")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
         InlineKeyboardButton(text="« Назад", callback_data="back_to_main")],
    ])


def get_deposit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Platega.io (RUB)", callback_data="deposit_platega"),
         InlineKeyboardButton(text="🤖 CryptoBot (USDT)", callback_data="deposit_cryptobot")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")],
    ])


def get_stars_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"100 ⭐ ({STARS_PRICES_RUB[100]:.0f} ₽)", callback_data="stars_100"),
         InlineKeyboardButton(text=f"500 ⭐ ({STARS_PRICES_RUB[500]:.0f} ₽)", callback_data="stars_500")],
        [InlineKeyboardButton(text=f"1000 ⭐ ({STARS_PRICES_RUB[1000]:.0f} ₽)", callback_data="stars_1000"),
         InlineKeyboardButton(text=f"5000 ⭐ ({STARS_PRICES_RUB[5000]:.0f} ₽)", callback_data="stars_5000")],
        [InlineKeyboardButton(text=f"10000 ⭐ ({STARS_PRICES_RUB[10000]:.0f} ₽)", callback_data="stars_10000"),
         InlineKeyboardButton(text="✨ Свое число", callback_data="stars_custom")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")],
    ])


async def get_premium_keyboard() -> InlineKeyboardMarkup:
    premium_tag = await get_premium_tag()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"3 {premium_tag} ({PREMIUM_PRICES_RUB[3]:.0f} ₽)", callback_data="premium_3"),
         InlineKeyboardButton(text=f"6 {premium_tag} ({PREMIUM_PRICES_RUB[6]:.0f} ₽)", callback_data="premium_6")],
        [InlineKeyboardButton(text=f"12 {premium_tag} ({PREMIUM_PRICES_RUB[12]:.0f} ₽)", callback_data="premium_12")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")],
    ])


def get_recipient_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Себе", callback_data="recipient_myself"),
         InlineKeyboardButton(text="🎁 Другому", callback_data="recipient_other")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")],
    ])


def get_confirm_keyboard(item_type: str, promocode_applied: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if not promocode_applied:
        buttons.append([InlineKeyboardButton(text="🎟️ Применить промокод", callback_data="apply_promocode")])
    buttons.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{item_type}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_purchase")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
    ])


def get_promocode_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo"),
         InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
        [InlineKeyboardButton(text="🗑️ Удалить промокод", callback_data="admin_delete_promo")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_panel")],
    ])


# ========== СОСТОЯНИЯ FSM ==========
class PurchaseState(StatesGroup):
    waiting_for_username = State()
    waiting_for_stars_amount = State()
    waiting_for_premium_months = State()
    waiting_for_custom_stars = State()
    waiting_for_promocode = State()
    waiting_for_recipient_choice = State()
    waiting_for_confirmation = State()
    waiting_for_deposit_amount = State()


class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_promo_code = State()
    waiting_for_promo_type = State()
    waiting_for_promo_value = State()
    waiting_for_promo_uses = State()
    waiting_for_promo_days = State()
    waiting_for_delete_promo = State()
    waiting_for_welcome_text = State()


# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = db.get_user(message.from_user.id)
    if not user:
        db.create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    db.update_last_active(message.from_user.id)
    
    welcome_text = db.get_welcome_text()
    welcome_text = await replace_premium_emoji(welcome_text, message.chat.id)
    
    await message.answer(welcome_text, reply_markup=await get_main_keyboard(), parse_mode="HTML")


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer("❌ Нет доступа")
        return
    await message.answer("📊 Админ-панель", reply_markup=get_admin_keyboard())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    premium_tag = await get_premium_tag()
    await message.answer(
        f"ℹ️ <b>Помощь</b>\n\n"
        f"<b>Доступные товары:</b>\n"
        f"⭐ Stars — 100-10000 шт.\n"
        f"{premium_tag} Premium — 3/6/12 месяцев\n\n"
        f"<b>Цены:</b>\n"
        f"Stars: 100⭐ = {STARS_PRICES_RUB[100]:.0f} ₽\n"
        f"Premium: 3 мес = {PREMIUM_PRICES_RUB[3]:.0f} ₽\n\n"
        f"<b>Пополнение:</b>\n"
        f"💳 Platega.io (RUB)\n🤖 CryptoBot (USDT)",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text("🏠 Главное меню", reply_markup=await get_main_keyboard())


# ========== ПОПОЛНЕНИЕ БАЛАНСА ==========
@dp.callback_query(F.data == "deposit_menu")
async def deposit_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("💰 Выберите способ пополнения:", reply_markup=get_deposit_keyboard())


@dp.callback_query(F.data == "deposit_platega")
async def deposit_platega(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_deposit_amount)
    await state.update_data(payment_system="platega")
    await callback.message.edit_text(
        f"💳 Введите сумму пополнения (RUB):\nМин: {db.get_min_deposit():.0f} ₽\nМакс: {db.get_max_deposit():.0f} ₽",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "deposit_cryptobot")
async def deposit_cryptobot(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_deposit_amount)
    await state.update_data(payment_system="cryptobot")
    await callback.message.edit_text(
        "🤖 Введите сумму пополнения (USDT):\nМин: 1 USDT\nМакс: 1000 USDT",
        reply_markup=get_back_keyboard()
    )


@dp.message(PurchaseState.waiting_for_deposit_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    payment_system = data.get("payment_system")
    
    try:
        amount = float(message.text.strip())
        if payment_system == "platega":
            if amount < db.get_min_deposit() or amount > db.get_max_deposit():
                await message.answer(f"❌ Сумма от {db.get_min_deposit():.0f} до {db.get_max_deposit():.0f} ₽")
                return
        else:
            if amount < 1 or amount > 1000:
                await message.answer("❌ Сумма от 1 до 1000 USDT")
                return
    except:
        await message.answer("❌ Введите число")
        return
    
    order_id = generate_order_id()
    await message.answer("⏳ Создание счета...")
    
    if payment_system == "platega":
        result = await PlategaPayment.create_invoice(amount, order_id, message.from_user.id)
        if result["success"]:
            db.add_payment(result["payment_id"], message.from_user.id, amount, "RUB", "platega")
            await message.answer(
                f"✅ Счет создан!\n💰 {amount:.2f} ₽\n🔗 <a href='{result['invoice_url']}'>Оплатить</a>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оплатить", url=result['invoice_url'])],
                    [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
                ])
            )
        else:
            await message.answer(f"❌ Ошибка: {result.get('error')}")
    else:
        result = await CryptoBotPayment.create_invoice(amount, order_id, message.from_user.id)
        if result["success"]:
            db.add_payment(result["payment_id"], message.from_user.id, amount, "USDT", "cryptobot")
            await message.answer(
                f"✅ Счет создан!\n💰 {amount:.2f} USDT\n🔗 <a href='{result['invoice_url']}'>Оплатить</a>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💎 Оплатить", url=result['invoice_url'])],
                    [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
                ])
            )
        else:
            await message.answer(f"❌ Ошибка: {result.get('error')}")
    
    await state.clear()


# ========== ПОКУПКА ==========
@dp.callback_query(F.data == "buy_stars")
async def buy_stars(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.update_data(purchase_type="stars")
    await state.set_state(PurchaseState.waiting_for_recipient_choice)
    await callback.message.edit_text("⭐ Выберите получателя:", reply_markup=get_recipient_keyboard())


@dp.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.update_data(purchase_type="premium")
    await state.set_state(PurchaseState.waiting_for_recipient_choice)
    await callback.message.edit_text("👑 Выберите получателя:", reply_markup=get_recipient_keyboard())


@dp.callback_query(F.data == "recipient_myself")
async def recipient_myself(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    purchase_type = data.get("purchase_type")
    username = callback.from_user.username or callback.from_user.first_name
    await state.update_data(username=username)
    
    if purchase_type == "stars":
        await state.set_state(PurchaseState.waiting_for_stars_amount)
        await callback.message.edit_text(f"👤 @{username}\n\nВыберите количество:", reply_markup=get_stars_keyboard())
    else:
        await state.set_state(PurchaseState.waiting_for_premium_months)
        await callback.message.edit_text(f"👤 @{username}\n\nВыберите срок:", reply_markup=await get_premium_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "recipient_other")
async def recipient_other(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.waiting_for_username)
    await callback.message.edit_text("Введите username получателя:", reply_markup=get_back_keyboard())
    await callback.answer()


@dp.message(PurchaseState.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
        await message.answer("❌ Некорректный username")
        return
    await state.update_data(username=username)
    data = await state.get_data()
    purchase_type = data.get("purchase_type")
    
    if purchase_type == "stars":
        await state.set_state(PurchaseState.waiting_for_stars_amount)
        await message.answer(f"👤 @{username}\n\nВыберите количество:", reply_markup=get_stars_keyboard())
    else:
        await state.set_state(PurchaseState.waiting_for_premium_months)
        await message.answer(f"👤 @{username}\n\nВыберите срок:", reply_markup=await get_premium_keyboard())


@dp.callback_query(F.data == "stars_custom")
async def stars_custom(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PurchaseState.waiting_for_custom_stars)
    await callback.message.edit_text("Введите количество Stars (1-100000):", reply_markup=get_back_keyboard())


@dp.message(PurchaseState.waiting_for_custom_stars)
async def process_custom_stars(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount < 1 or amount > 100000:
            raise ValueError
    except:
        await message.answer("❌ Введите число от 1 до 100000")
        return
    
    data = await state.get_data()
    username = data.get("username")
    price = amount * 0.57
    await state.update_data(item_type="stars", item_amount=amount, price=price)
    await state.set_state(PurchaseState.waiting_for_confirmation)
    
    user = db.get_user(message.from_user.id)
    balance = user.get("balance_rub", 0) if user else 0
    
    if balance >= price:
        await message.answer(
            f"🛒 Подтверждение\n\n⭐ Stars: {amount} шт.\n👤 @{username}\n💰 {price:.2f} ₽\n💳 Баланс: {balance:.2f} ₽",
            reply_markup=get_confirm_keyboard("stars")
        )
    else:
        await message.answer(f"❌ Недостаточно средств!\n💰 Баланс: {balance:.2f} ₽\n💰 Нужно: {price:.2f} ₽", reply_markup=await get_main_keyboard())
        await state.clear()


@dp.callback_query(F.data.startswith("stars_"))
async def process_stars_amount(callback: CallbackQuery, state: FSMContext):
    if callback.data == "stars_custom":
        return
    amount = int(callback.data.split("_")[1])
    data = await state.get_data()
    username = data.get("username")
    price = STARS_PRICES_RUB.get(amount, amount * 0.57)
    await state.update_data(item_type="stars", item_amount=amount, price=price)
    await state.set_state(PurchaseState.waiting_for_confirmation)
    
    user = db.get_user(callback.from_user.id)
    balance = user.get("balance_rub", 0) if user else 0
    
    if balance >= price:
        await callback.message.edit_text(
            f"🛒 Подтверждение\n\n⭐ Stars: {amount} шт.\n👤 @{username}\n💰 {price:.2f} ₽\n💳 Баланс: {balance:.2f} ₽",
            reply_markup=get_confirm_keyboard("stars")
        )
    else:
        await callback.message.edit_text(f"❌ Недостаточно средств!\n💰 Баланс: {balance:.2f} ₽\n💰 Нужно: {price:.2f} ₽", reply_markup=await get_main_keyboard())
        await state.clear()
    await callback.answer()


@dp.callback_query(F.data.startswith("premium_"))
async def process_premium_months(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    data = await state.get_data()
    username = data.get("username")
    price = PREMIUM_PRICES_RUB.get(months, months * 570)
    await state.update_data(item_type="premium", item_amount=months, price=price)
    await state.set_state(PurchaseState.waiting_for_confirmation)
    
    user = db.get_user(callback.from_user.id)
    balance = user.get("balance_rub", 0) if user else 0
    
    if balance >= price:
        await callback.message.edit_text(
            f"🛒 Подтверждение\n\n👑 Premium: {months} мес.\n👤 @{username}\n💰 {price:.2f} ₽\n💳 Баланс: {balance:.2f} ₽",
            reply_markup=get_confirm_keyboard("premium")
        )
    else:
        await callback.message.edit_text(f"❌ Недостаточно средств!\n💰 Баланс: {balance:.2f} ₽\n💰 Нужно: {price:.2f} ₽", reply_markup=await get_main_keyboard())
        await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "apply_promocode")
async def apply_promocode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.waiting_for_promocode)
    await callback.message.edit_text("🎟️ Введите промокод:", reply_markup=get_back_keyboard())
    await callback.answer()


@dp.message(PurchaseState.waiting_for_promocode)
async def process_promocode(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    validation = db.validate_promocode(code)
    if not validation["valid"]:
        await message.answer(validation.get("error", "❌ Недействительный промокод"))
        return
    
    data = await state.get_data()
    original_price = data.get("price", 0)
    discounted_price = db.apply_discount(original_price, validation["discount_type"], validation["discount_value"])
    await state.update_data(promocode=code, price=discounted_price, discount_applied=True)
    
    await message.answer(
        f"✅ Промокод активирован! Скидка: {validation['discount_value']}{'%' if validation['discount_type'] == 'percent' else ' ₽'}\n💰 {original_price:.2f} ₽ → {discounted_price:.2f} ₽",
        reply_markup=get_confirm_keyboard(data.get("item_type", "stars"), True)
    )
    await state.set_state(PurchaseState.waiting_for_confirmation)


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_purchase(callback: CallbackQuery, state: FSMContext):
    await callback.answer("⏳ Обработка...")
    data = await state.get_data()
    username = data.get("username")
    item_type = data.get("item_type")
    item_amount = data.get("item_amount")
    price = data.get("price")
    
    user = db.get_user(callback.from_user.id)
    if user.get("balance_rub", 0) < price:
        await callback.message.edit_text("❌ Недостаточно средств", reply_markup=await get_main_keyboard())
        await state.clear()
        return
    
    db.deduct_balance(callback.from_user.id, price)
    await callback.message.edit_text(f"⏳ Отправка в Fragment API...\n💰 {price:.2f} ₽\n👤 @{username}")
    
    try:
        async with FragmentService() as fragment:
            if item_type == "stars":
                result = await fragment.buy_stars(username, item_amount)
            else:
                result = await fragment.buy_premium(username, item_amount)
        
        if result.get("success"):
            purchase = db.add_purchase(callback.from_user.id, item_type, item_amount, username, price, result.get("transaction_id", "unknown"))
            stars = item_amount if item_type == "stars" else 0
            premium_months = item_amount if item_type == "premium" else 0
            db.update_user_stats(callback.from_user.id, stars, premium_months)
            
            emoji_item = "⭐" if item_type == "stars" else await get_premium_tag()
            await callback.message.edit_text(
                f"✅ Покупка выполнена!\n\n🆔 ID: {purchase['order_id']}\n{emoji_item} {item_amount} {'⭐' if item_type == 'stars' else 'мес.'}\n👤 @{username}\n💰 {price:.2f} ₽",
                reply_markup=await get_main_keyboard(),
                parse_mode="HTML"
            )
        else:
            db.update_balance(callback.from_user.id, price)
            await callback.message.edit_text(f"❌ Ошибка: {result.get('error')}", reply_markup=await get_main_keyboard())
    except Exception as e:
        db.update_balance(callback.from_user.id, price)
        await callback.message.edit_text(f"❌ Ошибка: {str(e)[:200]}", reply_markup=await get_main_keyboard())
    
    await state.clear()


@dp.callback_query(F.data == "cancel_purchase")
async def cancel_purchase(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("❌ Отменено")
    await callback.message.edit_text("❌ Покупка отменена", reply_markup=await get_main_keyboard())


# ========== ПРОЧИЕ ОБРАБОТЧИКИ ==========
@dp.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    balance = user.get("balance_rub", 0) if user else 0
    await callback.message.edit_text(
        f"💰 Ваш баланс: {balance:.2f} ₽\n\n💳 Пополнить: кнопка ниже",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit_menu")],
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery):
    purchases = db.get_user_purchases(callback.from_user.id, limit=10)
    if not purchases:
        await callback.message.edit_text("📜 История пуста", reply_markup=get_back_keyboard())
        return
    text = "📜 История покупок\n\n"
    for p in purchases:
        emoji = "⭐" if p["type"] == "stars" else "👑"
        text += f"{emoji} {p['order_id']} | @{p['recipient']} | {p['amount']} | {p['price_rub']:.2f} ₽\n"
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)


# ========== АДМИН-ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text("📊 Админ-панель", reply_markup=get_admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    stats = db.get_stats()
    await callback.message.edit_text(
        f"📊 Статистика\n\n👥 Пользователи: {stats['total_users']}\n🛒 Покупок: {stats['total_purchases']}\n💰 Объем: {stats['total_volume']:.2f} ₽",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_purchases")
async def admin_purchases(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    purchases = db.get_all_purchases(20)
    if not purchases:
        await callback.message.edit_text("Нет покупок", reply_markup=get_admin_keyboard())
        return
    text = "📦 Последние покупки\n\n"
    for p in purchases[:10]:
        emoji = "⭐" if p["type"] == "stars" else "👑"
        text += f"{emoji} {p['order_id']} | {p['user_id']} | {p['amount']} | {p['price_rub']:.2f} ₽\n"
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    stats = db.get_stats()
    await callback.message.edit_text(
        f"👥 Пользователи: {stats['total_users']}\n\nКоманды:\n/ban [id]\n/unban [id]",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.edit_text("📢 Введите текст рассылки:", reply_markup=get_back_keyboard())
    await callback.answer()


@dp.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    users = db.get_all_users()
    broadcast_id = db.add_broadcast(message.text, message.from_user.id)
    sent = 0
    await message.answer(f"📢 Рассылка... Всего: {len(users)}")
    for user in users:
        try:
            await bot.send_message(user["user_id"], f"📢 Рассылка\n\n{message.text}", parse_mode="HTML")
            sent += 1
        except:
            pass
        await asyncio.sleep(0.05)
    db.update_broadcast_stats(broadcast_id, sent)
    await message.answer(f"✅ Рассылка завершена!\n✅ Отправлено: {sent}", reply_markup=get_admin_keyboard())
    await state.clear()


@dp.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text(
        f"⚙️ Настройки\n\nТестовый режим: {'🟢 Вкл' if TEST_MODE else '🔴 Выкл'}\n\nКоманды:\n/set_welcome [текст]\n/maintenance",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_update_emoji")
async def admin_update_emoji(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    await callback.answer("🔄 Обновление...")
    result = await EmojiIDDetector.get_emoji_id("👑", callback.message.chat.id)
    if result["success"]:
        premium_tag = EmojiIDDetector.create_tg_emoji_tag("👑", result["emoji_id"])
        await callback.message.edit_text(
            f"✅ Премиум эмодзи обновлен!\n👑 ID: {result['emoji_id']}\n📋 {premium_tag}",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(f"❌ Ошибка: {result.get('error')}", reply_markup=get_admin_keyboard())


@dp.callback_query(F.data == "admin_promocodes")
async def admin_promocodes(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text("🎟️ Управление промокодами", reply_markup=get_promocode_admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "admin_create_promo")
async def admin_create_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_promo_code)
    await callback.message.edit_text("Введите код промокода:", reply_markup=get_back_keyboard())
    await callback.answer()


@dp.message(AdminState.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    await state.set_state(AdminState.waiting_for_promo_type)
    await message.answer(
        f"Код: {code}\n\nВыберите тип:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="% Процент", callback_data="promo_type_percent"),
             InlineKeyboardButton(text="💰 Фиксированная", callback_data="promo_type_fixed")]
        ])
    )


@dp.callback_query(F.data.startswith("promo_type_"))
async def process_promo_type(callback: CallbackQuery, state: FSMContext):
    discount_type = callback.data.split("_")[2]
    await state.update_data(discount_type=discount_type)
    await state.set_state(AdminState.waiting_for_promo_value)
    await callback.message.edit_text("Введите размер скидки:", reply_markup=get_back_keyboard())
    await callback.answer()


@dp.message(AdminState.waiting_for_promo_value)
async def process_promo_value(message: Message, state: FSMContext):
    try:
        value = float(message.text.strip())
    except:
        await message.answer("❌ Введите число")
        return
    await state.update_data(discount_value=value)
    await state.set_state(AdminState.waiting_for_promo_uses)
    await message.answer("Введите количество использований (0 - безлимит):")


@dp.message(AdminState.waiting_for_promo_uses)
async def process_promo_uses(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text.strip())
        if max_uses == 0:
            max_uses = 999999
    except:
        await message.answer("❌ Введите число")
        return
    await state.update_data(max_uses=max_uses)
    await state.set_state(AdminState.waiting_for_promo_days)
    await message.answer("Введите срок действия (дней, 0 - бессрочно):")


@dp.message(AdminState.waiting_for_promo_days)
async def process_promo_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
    except:
        await message.answer("❌ Введите число")
        return
    data = await state.get_data()
    success = db.create_promocode(data["promo_code"], data["discount_type"], data["discount_value"], data["max_uses"], days, message.from_user.id)
    if success:
        await message.answer(f"✅ Промокод {data['promo_code']} создан!", reply_markup=get_admin_keyboard())
    else:
        await message.answer(f"❌ Ошибка", reply_markup=get_admin_keyboard())
    await state.clear()


@dp.callback_query(F.data == "admin_list_promos")
async def admin_list_promos(callback: CallbackQuery):
    promos = db.get_all_promocodes()
    if not promos:
        await callback.message.edit_text("Нет промокодов", reply_markup=get_promocode_admin_keyboard())
        return
    text = "🎟️ Список промокодов\n\n"
    for p in promos[:10]:
        text += f"<code>{p['code']}</code> | {p['discount_value']}{'%' if p['discount_type'] == 'percent' else ' ₽'} | {p['used_count']}/{p['max_uses']}\n"
    await callback.message.edit_text(text, reply_markup=get_promocode_admin_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "admin_delete_promo")
async def admin_delete_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_delete_promo)
    await callback.message.edit_text("Введите код промокода:", reply_markup=get_back_keyboard())
    await callback.answer()


@dp.message(AdminState.waiting_for_delete_promo)
async def process_delete_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    success = db.delete_promocode(code)
    await message.answer(f"{'✅' if success else '❌'} Промокод {code} {'удален' if success else 'не найден'}", reply_markup=get_admin_keyboard())
    await state.clear()


@dp.message(Command("set_welcome"))
async def set_welcome_text(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer("❌ Нет доступа")
        return
    text = message.text.replace("/set_welcome", "").strip()
    if not text:
        await message.answer("❌ Использование: /set_welcome [текст]\nДля вставки эмодзи используйте {premium}")
        return
    db.set_welcome_text(text)
    preview = await replace_premium_emoji(text, message.chat.id)
    await message.answer(f"✅ Обновлено!\n\nПревью:\n{preview}", parse_mode="HTML")


@dp.message(Command("maintenance"))
async def maintenance_mode(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer("❌ Нет доступа")
        return
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    await message.answer(f"⚙️ Режим обслуживания {'включен' if MAINTENANCE_MODE else 'выключен'}")


@dp.message(Command("ban"))
async def ban_user(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ /ban [user_id]")
        return
    try:
        user_id = int(args[1])
        db.block_user(user_id, True)
        await message.answer(f"✅ Пользователь {user_id} заблокирован")
    except:
        await message.answer("❌ Неверный ID")


@dp.message(Command("unban"))
async def unban_user(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ /unban [user_id]")
        return
    try:
        user_id = int(args[1])
        db.block_user(user_id, False)
        await message.answer(f"✅ Пользователь {user_id} разблокирован")
    except:
        await message.answer("❌ Неверный ID")


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("❌ Операция отменена", reply_markup=await get_main_keyboard())
    else:
        await message.answer("Нет активных операций")


@dp.message()
async def handle_unknown(message: Message):
    await message.answer("❌ Неизвестная команда. Используйте /help", reply_markup=await get_main_keyboard())


# ========== ЗАПУСК ==========
async def main():
    print("🚀 Fragment Bot запускается...")
    print("💰 Все цены в рублях")
    print("💳 Platega.io и CryptoBot для пополнения")
    print("⭐ Fragment API для автопополнения")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
