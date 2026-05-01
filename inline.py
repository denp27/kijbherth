from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import STARS_PRICES, PREMIUM_PRICES, PREMIUM_EMOJI_IDS, ADMIN_IDS


def get_main_menu(user_id: int = None):
    """Главное меню с цветными кнопками"""
    buttons = [
        [
            InlineKeyboardButton(
                text="Магазин",
                callback_data="shop",
                icon_custom_emoji_id=PREMIUM_EMOJI_IDS["shop"]
            ),
            InlineKeyboardButton(
                text="Профиль",
                callback_data="profile",
                icon_custom_emoji_id=PREMIUM_EMOJI_IDS["profile"]
            ),
        ],
        [
            InlineKeyboardButton(
                text="💰 Пополнить",
                callback_data="topup",
                icon_custom_emoji_id=PREMIUM_EMOJI_IDS["balance"]
            ),
            InlineKeyboardButton(
                text="🎟️ Промокод",
                callback_data="promo",
                icon_custom_emoji_id=PREMIUM_EMOJI_IDS["gift"]
            ),
        ],
        [
            InlineKeyboardButton(
                text="👥 Рефералы",
                callback_data="referral_info",
                icon_custom_emoji_id=PREMIUM_EMOJI_IDS["users"]
            ),
            InlineKeyboardButton(
                text="📋 Задания",
                callback_data="tasks_section",
                icon_custom_emoji_id=PREMIUM_EMOJI_IDS["tasks"]
            ),
        ],
    ]
    
    if user_id and user_id in ADMIN_IDS:
        buttons.append([
            InlineKeyboardButton(
                text="🔧 Админ панель",
                callback_data="admin_panel",
                icon_custom_emoji_id=PREMIUM_EMOJI_IDS["settings"]
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_menu():
    """Админ меню с цветными кнопками"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"), InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing"), InlineKeyboardButton(text="🎟️ Промокоды", callback_data="admin_promocodes")],
            [InlineKeyboardButton(text="📋 Задания", callback_data="admin_tasks"), InlineKeyboardButton(text="⚙️ Цены", callback_data="admin_prices")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
        ]
    )


def get_shop_menu(balance: float):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="buy_stars"), InlineKeyboardButton(text="💎 Купить Premium", callback_data="buy_premium")],
            [InlineKeyboardButton(text=f"💰 Баланс: {balance}₽", callback_data="balance"), InlineKeyboardButton(text="🎁 Подарки", callback_data="gifts")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
        ]
    )


def get_stars_packs():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="50 ⭐ - 59₽", callback_data="stars_50"), InlineKeyboardButton(text="100 ⭐ - 99₽", callback_data="stars_100")],
            [InlineKeyboardButton(text="250 ⭐ - 229₽", callback_data="stars_250"), InlineKeyboardButton(text="500 ⭐ - 429₽", callback_data="stars_500")],
            [InlineKeyboardButton(text="1000 ⭐ - 799₽", callback_data="stars_1000"), InlineKeyboardButton(text="2500 ⭐ - 1899₽", callback_data="stars_2500")],
            [InlineKeyboardButton(text="5000 ⭐ - 3599₽", callback_data="stars_5000")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")],
        ]
    )


def get_premium_packs():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="3 месяца - 299₽", callback_data="premium_3"), InlineKeyboardButton(text="6 месяцев - 499₽", callback_data="premium_6")],
            [InlineKeyboardButton(text="12 месяцев - 799₽", callback_data="premium_12")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")],
        ]
    )


def get_payment_methods_keyboard(amount: float, topup_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🪙 CryptoBot (USDT)", callback_data=f"pay_cryptobot_{topup_id}_{amount}"), InlineKeyboardButton(text="💳 Platega.io", callback_data=f"pay_platega_{topup_id}_{amount}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="topup")],
        ]
    )


def get_topup_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="100₽", callback_data="topup_100"), InlineKeyboardButton(text="250₽", callback_data="topup_250"), InlineKeyboardButton(text="500₽", callback_data="topup_500")],
            [InlineKeyboardButton(text="1000₽", callback_data="topup_1000"), InlineKeyboardButton(text="2500₽", callback_data="topup_2500"), InlineKeyboardButton(text="5000₽", callback_data="topup_5000")],
            [InlineKeyboardButton(text="💰 Своя сумма", callback_data="topup_custom")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")],
        ]
    )


def get_insufficient_balance_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")],
        ]
    )


def get_back_to_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_main")],
        ]
    )


def get_mailing_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Текстовая рассылка", callback_data="mailing_text")],
            [InlineKeyboardButton(text="🖼️ Медиа-рассылка", callback_data="mailing_media")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
        ]
    )


def get_mailing_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="mailing_send")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_mailing")],
        ]
    )


def get_admin_users_list(users, page=0):
    keyboard = []
    for user in users[page*5:(page+1)*5]:
        status = "🔴" if user['is_banned'] else "🟢"
        name = user['first_name'] or user['username'] or str(user['user_id'])
        keyboard.append([InlineKeyboardButton(text=f"{status} {name} | 💰{user['balance']}₽", callback_data=f"admin_user_{user['user_id']}")])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_users_page_{page-1}"))
    if len(users) > (page+1)*5:
        nav.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_users_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_user_actions(user_id: int, is_banned: bool):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Разбанить" if is_banned else "🔒 Забанить", callback_data=f"admin_ban_{user_id}"), InlineKeyboardButton(text="💰 Пополнить", callback_data=f"admin_add_balance_{user_id}")],
            [InlineKeyboardButton(text="📜 История", callback_data=f"admin_user_history_{user_id}"), InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")],
        ]
    )


def get_admin_prices_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Изменить цены на Stars", callback_data="admin_edit_stars")],
            [InlineKeyboardButton(text="💎 Изменить цены на Premium", callback_data="admin_edit_premium")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
        ]
    )
