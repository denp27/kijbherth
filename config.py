import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = "7867924002:AAHtXRQoZXuaL7IhnGqD03pTf4yzWIIAVz4"

# ID премиум эмодзи для кнопок
PREMIUM_EMOJI_IDS = {
    "premium": "5471952986970267163",
    "profile": "5368324170671202286",
    "shop": "5447644880824181073",
    "tasks": "5445284980978621387",
    "delete": "5310169226856644648",
    "cancel": "5310076249404621168",
    "check": "5310076249404621168",
    "back": "5310076249404621168",
    "stars": "5447644880824181073",
    "gift": "5445284980978621387",
    "balance": "5471952986970267163",
    "history": "5368324170671202286",
    "settings": "5310076249404621168",
    "users": "5368324170671202286",
    "stats": "5471952986970267163",
    "mail": "5447644880824181073",
    "rocket": "5310076249404621168",
    "add": "5310076249404621168",
    "next": "5310076249404621168",
}


def get_premium_emoji(emoji_key: str = "premium") -> str:
    return f'<tg-emoji emoji-id="{PREMIUM_EMOJI_IDS.get(emoji_key, PREMIUM_EMOJI_IDS["premium"])}"> </tg-emoji>'


ADMIN_IDS = [8429942952]

REFERRAL_REWARD_PERCENT = 10
REFERRAL_BONUS = 50

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN", "")
CRYPTOBOT_IS_MAINNET = True

PLATEGA_MERCHANT_ID = os.getenv("PLATEGA_MERCHANT_ID", "")
PLATEGA_SECRET_KEY = os.getenv("PLATEGA_SECRET_KEY", "")
PLATEGA_API_URL = "https://platega.io/api"

STARS_PRICES = {50: 59, 100: 99, 250: 229, 500: 429, 1000: 799, 2500: 1899, 5000: 3599}
PREMIUM_PRICES = {3: 299, 6: 499, 12: 799}

SUPPORT_EMAIL = "support@example.com"
SUPPORT_ADMIN = "admin_username"

# Fragment данные
FRAGMENT_SEED = os.getenv("FRAGMENT_SEED", "")
FRAGMENT_API_KEY = os.getenv("FRAGMENT_API_KEY", "")
FRAGMENT_COOKIES = {
    "stel_ssid": os.getenv("STEL_SSID", ""),
    "stel_dt": os.getenv("STEL_DT", ""),
    "stel_token": os.getenv("STEL_TOKEN", ""),
    "stel_ton_token": os.getenv("STEL_TON_TOKEN", ""),
}


print(f"✅ BOT_TOKEN загружен: {BOT_TOKEN[:15]}...")
print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
