import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

DB_NAME = "bot_database.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL DEFAULT 0,
        is_banned BOOLEAN DEFAULT 0,
        registered_at TIMESTAMP,
        total_spent REAL DEFAULT 0,
        total_earned REAL DEFAULT 0,
        referral_code TEXT UNIQUE,
        referred_by INTEGER DEFAULT NULL,
        referral_earnings REAL DEFAULT 0,
        referral_count INTEGER DEFAULT 0
    )''')

    # Purchases table
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount INTEGER,
        price REAL,
        status TEXT DEFAULT 'pending',
        payment_system TEXT,
        payment_id TEXT,
        transaction_id TEXT,
        order_number TEXT UNIQUE,
        created_at TIMESTAMP,
        completed_at TIMESTAMP,
        gift_to_id TEXT DEFAULT NULL,
        is_gift BOOLEAN DEFAULT 0
    )''')

    # Balance topups table
    c.execute('''CREATE TABLE IF NOT EXISTS balance_topups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'pending',
        payment_system TEXT,
        payment_id TEXT,
        transaction_id TEXT,
        created_at TIMESTAMP,
        completed_at TIMESTAMP
    )''')

    # Promocodes table
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY,
        reward REAL,
        max_uses INTEGER,
        used_count INTEGER DEFAULT 0,
        expires_at TIMESTAMP,
        created_at TIMESTAMP
    )''')

    # Used promocodes
    c.execute('''CREATE TABLE IF NOT EXISTS used_promocodes (
        user_id INTEGER,
        code TEXT,
        used_at TIMESTAMP,
        PRIMARY KEY (user_id, code)
    )''')

    # Tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        task_type TEXT,
        target TEXT,
        reward REAL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP
    )''')

    # User tasks
    c.execute('''CREATE TABLE IF NOT EXISTS user_tasks (
        user_id INTEGER,
        task_id INTEGER,
        status TEXT DEFAULT 'pending',
        proof TEXT,
        completed_at TIMESTAMP,
        reviewed_by INTEGER DEFAULT NULL,
        reviewed_at TIMESTAMP,
        PRIMARY KEY (user_id, task_id)
    )''')

    # Settings
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # Insert default promocodes
    c.execute('''INSERT OR IGNORE INTO promocodes (code, reward, max_uses, expires_at, created_at)
                 VALUES ('WELCOME50', 50, 1000, ?, ?)''', 
              (datetime.now().replace(year=datetime.now().year + 1), datetime.now()))

    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'false')")
    conn.commit()
    conn.close()


def generate_order_number() -> str:
    """Генерация уникального номера заказа"""
    import random
    import string
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{timestamp}-{random_chars}"


def get_user(user_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_referral_code(code: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


def create_user(user_id: int, username: str = "", first_name: str = "", referred_by: int = None):
    import hashlib
    
    referral_code = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()[:8]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, registered_at, referral_code, referred_by)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, username, first_name, datetime.now(), referral_code, referred_by))
    if referred_by:
        c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referred_by,))
        from config import REFERRAL_BONUS
        c.execute("UPDATE users SET balance = balance + ?, referral_earnings = referral_earnings + ? WHERE user_id = ?",
                  (REFERRAL_BONUS, REFERRAL_BONUS, referred_by))
    conn.commit()
    conn.close()


def update_balance(user_id: int, amount: float):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    if amount > 0:
        c.execute("UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def deduct_balance(user_id: int, amount: float) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result and result[0] >= amount:
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def get_balance(user_id: int) -> float:
    user = get_user(user_id)
    return user['balance'] if user else 0


def ban_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def unban_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_users() -> List[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY registered_at DESC")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return users


def add_purchase(user_id: int, purchase_type: str, amount: int, price: float,
                 payment_system: str, gift_to_id: str = None, is_gift: bool = False) -> int:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    order_number = generate_order_number()
    c.execute('''INSERT INTO purchases (user_id, type, amount, price, status, payment_system, order_number, created_at, gift_to_id, is_gift)
                 VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)''',
              (user_id, purchase_type, amount, price, payment_system, order_number, datetime.now(), gift_to_id, is_gift))
    purchase_id = c.lastrowid
    conn.commit()
    conn.close()
    return purchase_id


def complete_purchase(purchase_id: int, transaction_id: str = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE purchases SET status = 'completed', transaction_id = ?, completed_at = ? WHERE id = ?",
              (transaction_id, datetime.now(), purchase_id))
    
    # Начисление реферального вознаграждения
    c.execute("SELECT user_id, price FROM purchases WHERE id = ?", (purchase_id,))
    purchase = c.fetchone()
    if purchase:
        user_id, price = purchase
        c.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,))
        referrer = c.fetchone()
        if referrer and referrer[0]:
            from config import REFERRAL_REWARD_PERCENT
            reward = price * REFERRAL_REWARD_PERCENT / 100
            c.execute("UPDATE users SET balance = balance + ?, referral_earnings = referral_earnings + ? WHERE user_id = ?",
                      (reward, reward, referrer[0]))
            c.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (price, user_id))
    
    conn.commit()
    conn.close()


def get_purchase(purchase_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,))
    purchase = c.fetchone()
    conn.close()
    return dict(purchase) if purchase else None


def get_user_purchases(user_id: int, limit: int = 10) -> List[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM purchases WHERE user_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT ?",
              (user_id, limit))
    purchases = [dict(row) for row in c.fetchall()]
    conn.close()
    return purchases


def add_balance_topup(user_id: int, amount: float, payment_system: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO balance_topups (user_id, amount, payment_system, created_at)
                 VALUES (?, ?, ?, ?)''', (user_id, amount, payment_system, datetime.now()))
    topup_id = c.lastrowid
    conn.commit()
    conn.close()
    return topup_id


def complete_balance_topup(topup_id: int, transaction_id: str = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, amount FROM balance_topups WHERE id = ?", (topup_id,))
    topup = c.fetchone()
    if topup:
        user_id, amount = topup
        update_balance(user_id, amount)
        c.execute("UPDATE balance_topups SET status = 'completed', transaction_id = ?, completed_at = ? WHERE id = ?",
                  (transaction_id, datetime.now(), topup_id))
    conn.commit()
    conn.close()


def add_promocode(code: str, reward: float, max_uses: int, expires_at: datetime):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO promocodes (code, reward, max_uses, expires_at, created_at)
                 VALUES (?, ?, ?, ?, ?)''', (code.upper(), reward, max_uses, expires_at, datetime.now()))
    conn.commit()
    conn.close()


def get_promocode(code: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM promocodes WHERE code = ?", (code.upper(),))
    promo = c.fetchone()
    conn.close()
    return dict(promo) if promo else None


def use_promocode(user_id: int, code: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    promo = get_promocode(code)
    if not promo:
        return False
    
    if promo['used_count'] >= promo['max_uses']:
        return False
    
    if promo['expires_at'] and datetime.now() > datetime.fromisoformat(promo['expires_at']):
        return False
    
    c.execute("SELECT * FROM used_promocodes WHERE user_id = ? AND code = ?", (user_id, code.upper()))
    if c.fetchone():
        return False
    
    c.execute("INSERT INTO used_promocodes (user_id, code, used_at) VALUES (?, ?, ?)",
              (user_id, code.upper(), datetime.now()))
    c.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code.upper(),))
    conn.commit()
    conn.close()
    return True


def apply_promocode_reward(user_id: int, code: str) -> float:
    promo = get_promocode(code)
    if promo and use_promocode(user_id, code):
        update_balance(user_id, promo['reward'])
        return promo['reward']
    return 0


def get_referrals(user_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE referred_by = ? ORDER BY registered_at DESC", (user_id,))
    referrals = [dict(row) for row in c.fetchall()]
    conn.close()
    return referrals


def get_stats() -> Dict:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(price) FROM purchases WHERE status = 'completed'")
    total_revenue = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM purchases WHERE status = 'completed'")
    total_purchases = c.fetchone()[0]
    
    c.execute("SELECT SUM(amount) FROM purchases WHERE type = 'stars' AND status = 'completed'")
    total_stars_sold = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM purchases WHERE type = 'premium' AND status = 'completed'")
    total_premium_sold = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(referral_earnings) FROM users")
    total_referral_paid = c.fetchone()[0] or 0
    
    today = datetime.now().date()
    c.execute("SELECT SUM(price) FROM purchases WHERE status = 'completed' AND DATE(completed_at) = ?", (today,))
    today_revenue = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_revenue': total_revenue,
        'total_purchases': total_purchases,
        'total_stars_sold': total_stars_sold,
        'total_premium_sold': total_premium_sold,
        'total_referral_paid': total_referral_paid,
        'today_revenue': today_revenue
    }
