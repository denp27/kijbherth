from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import STARS_PRICES, PREMIUM_PRICES, PREMIUM_EMOJI_IDS, ADMIN_IDS
from typing import List, Dict


def get_main_menu(user_id: int = None):
    """Главное меню с цветными кнопками"""
    buttons = [
        [
            InlineKeyboardButton(
                text="Магазин",
                callback_data="shop",
            ),
            InlineKeyboardButton(
                text="Профиль",
                callback_data="profile",
            ),
        ],
        [
            InlineKeyboardButton(
                text="💰 Пополнить",
                callback_data="topup",
            ),
            InlineKeyboardButton(
                text="🎟️ Промокод",
                callback_data="promo",
            ),
        ],
        [
            InlineKeyboardButton(
                text="👥 Рефералы",
                callback_data="referral_info",
            ),
            InlineKeyboardButton(
                text="📋 Задания",
                callback_data="tasks_section",
            ),
        ],
    ]
    
    if user_id and user_id in ADMIN_IDS:
        buttons.append([
            InlineKeyboardButton(
                text="🔧 Админ панель",
                callback_data="admin_panel",
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


# ============= ДОБАВЛЕННЫЕ ФУНКЦИИ ДЛЯ ЗАДАНИЙ =============

def tasks_keyboard(tasks: List[Dict], completed_ids: List[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура со списком заданий"""
    keyboard = []
    
    if not tasks:
        keyboard.append([InlineKeyboardButton(text="📭 Нет доступных заданий", callback_data="noop")])
    else:
        for task in tasks:
            if completed_ids and task['id'] in completed_ids:
                status = "✅"
            else:
                status = "📋"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {task['title']} - {task['reward']}⭐",
                    callback_data=f"task_{task['id']}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def task_detail_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура деталей задания"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать выполнение", callback_data=f"task_start_{task_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_section")]
    ])
    return keyboard


def confirm_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения выполнения"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Проверить выполнение", callback_data=f"task_check_{task_id}")],
        [InlineKeyboardButton(text="📎 Отправить доказательство", callback_data=f"task_proof_{task_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_section")]
    ])
    return keyboard


def back_keyboard(task_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой назад"""
    if task_id:
        back_callback = f"task_{task_id}"
    else:
        back_callback = "tasks_section"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)]
    ])
    return keyboard


def task_approve_keyboard(task_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для админа - подтверждение/отклонение задания"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"task_approve_{task_id}_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"task_reject_{task_id}_{user_id}")
        ]
    ])
    return keyboard


# ============= ДОБАВЛЕННЫЕ АДМИН-ФУНКЦИИ ДЛЯ ЗАДАНИЙ =============

def get_admin_tasks_keyboard(tasks: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура для управления заданиями (админ)"""
    keyboard = []
    
    for task in tasks:
        status = "✅" if task.get('is_active', 1) else "❌"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {task['title']} ({task['reward']}⭐)",
                callback_data=f"admin_edit_task_{task['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="➕ Создать задание", callback_data="admin_create_task")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_pending_keyboard(tasks: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра заявок (админ)"""
    keyboard = []
    
    if tasks:
        for task in tasks:
            username = task.get('username') or task.get('first_name') or str(task.get('user_id', 'Unknown'))
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📝 {username} - {task.get('title', 'Задание')}",
                    callback_data=f"admin_view_task_{task.get('task_id')}_{task.get('user_id')}"
                )
            ])
    else:
        keyboard.append([InlineKeyboardButton(text="📭 Нет заявок на проверку", callback_data="noop")])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirm_action_keyboard(action: str, task_id: int = None, user_id: int = None) -> InlineKeyboardMarkup:
    """Универсальная клавиатура подтверждения действия"""
    if task_id and user_id:
        confirm_callback = f"{action}_{task_id}_{user_id}"
    else:
        confirm_callback = action
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
        ]
    ])
    return keyboard


# ============= ДОПОЛНИТЕЛЬНЫЕ ПОЛЕЗНЫЕ КЛАВИАТУРЫ =============

def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton(text="🎫 Ввести промокод", callback_data="enter_promocode")],
        [InlineKeyboardButton(text="📜 История покупок", callback_data="purchase_history")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard


def get_referral_keyboard(referral_code: str) -> InlineKeyboardMarkup:
    """Реферальная клавиатура"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Поделиться ссылкой", switch_inline_query=referral_code)],
        [InlineKeyboardButton(text="📊 Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard


def get_promo_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ввода промокода"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Ввести промокод", callback_data="enter_promocode")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_profile")]
    ])
    return keyboard


def get_promocode_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления промокодами (админ)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promocode")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promocodes")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_settings")]
    ])
    return keyboard


def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек (админ)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Режим обслуживания", callback_data="admin_toggle_maintenance")],
        [InlineKeyboardButton(text="🎫 Управление промокодами", callback_data="admin_promocodes")],
        [InlineKeyboardButton(text="⚙️ Настройка бонусов", callback_data="admin_bonus_settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])
    return keyboard


# Алиасы для обратной совместимости с handlers/tasks.py
tasks_keyboard_alias = tasks_keyboard
task_detail_keyboard_alias = task_detail_keyboard
confirm_keyboard_alias = confirm_keyboard
back_keyboard_alias = back_keyboard
task_approve_keyboard_alias = task_approve_keyboard
