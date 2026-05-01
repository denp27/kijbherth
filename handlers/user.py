# /app/handlers/user.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from database import (
    get_user, 
    create_user, 
    update_balance, 
    get_user_purchases, 
    get_balance,
    get_promocode,
    use_promocode
)
from keyboards import get_main_menu, get_topup_menu, get_back_to_main_keyboard
from config import REFERRAL_BONUS, REFERRAL_REWARD_PERCENT, ADMIN_IDS

# Убираем get_premium_emoji, используем простые эмодзи
def get_simple_emoji() -> str:
    return "⭐"

router = Router()


class TopUpState(StatesGroup):
    waiting_for_amount = State()


class PromoState(StatesGroup):
    waiting_for_code = State()


@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    referred_by = None
    if len(args) > 1:
        from database import get_user_by_referral_code
        referrer = get_user_by_referral_code(args[1])
        if referrer and referrer['user_id'] != message.from_user.id:
            referred_by = referrer['user_id']
    
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        create_user(user_id, message.from_user.username or "", message.from_user.first_name or "", referred_by)
        user = get_user(user_id)
        if referred_by:
            await message.answer(f"🎉 Вы приглашены другом! Бонус {REFERRAL_BONUS}₽ зачислен!")
    
    if user and user.get('is_banned'):
        await message.answer("❌ Ваш аккаунт заблокирован.")
        return
    
    balance = user['balance'] if user else 0
    
    # Используем простой текст без сложных эмодзи
    text = f"""⭐ Добро пожаловать в Telegram Stars & Premium Bot! ⭐

Здесь вы можете купить Telegram Stars и Premium подписку

💰 Ваш баланс: {balance}₽

🚀 Выберите действие:"""
    
    await message.answer(text, reply_markup=get_main_menu(user_id))


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await cmd_start(message)
        return
    
    balance = user['balance'] if user else 0
    text = f"""⭐ Главное меню ⭐

💰 Ваш баланс: {balance}₽"""
    
    await message.answer(text, reply_markup=get_main_menu(message.from_user.id))


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await cmd_start(message)
        return
    
    balance = user['balance'] if user else 0
    await message.answer(f"💰 Ваш баланс: {balance}₽")


@router.message(Command("myid"))
async def get_my_id(message: Message):
    await message.answer(f"✅ Ваш ID: {message.from_user.id}")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    balance = user['balance'] if user else 0
    text = f"""⭐ Главное меню ⭐

💰 Ваш баланс: {balance}₽"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu(callback.from_user.id))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_main_menu(callback.from_user.id))
    
    await callback.answer()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    purchases = get_user_purchases(callback.from_user.id, 5)
    
    purchases_text = ""
    if purchases:
        for p in purchases[:3]:
            purchases_text += f"• Заказ #{p.get('order_number', 'N/A')}: {p.get('type', 'N/A').upper()} - {p.get('price', 0)}₽\n"
    else:
        purchases_text = "• Нет покупок"
    
    registered_at = user.get('registered_at', 'Неизвестно')
    if registered_at and len(registered_at) > 10:
        registered_at = registered_at[:10]
    
    text = f"""⭐ Мой профиль ⭐

🆔 ID: {user['user_id']}
👤 Имя: {user.get('first_name', 'Без имени')}
💰 Баланс: {user.get('balance', 0)}₽
💸 Потрачено: {user.get('total_spent', 0)}₽
👥 Рефералов: {user.get('referral_count', 0)}
🎁 Заработано с рефералов: {user.get('referral_earnings', 0)}₽
📅 Регистрация: {registered_at}

📜 Последние покупки:
{purchases_text}"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard())
    except Exception as e:
        try:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=get_back_to_main_keyboard())
        except:
            pass
    
    await callback.answer()


@router.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    balance = user.get('balance', 0)
    
    try:
        await callback.message.edit_text(
            f"💰 Ваш баланс: {balance}₽",
            reply_markup=get_back_to_main_keyboard()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            f"💰 Ваш баланс: {balance}₽",
            reply_markup=get_back_to_main_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "topup")
async def topup_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "💰 Пополнение баланса\n\nВыберите сумму:",
            reply_markup=get_topup_menu()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "💰 Пополнение баланса\n\nВыберите сумму:",
            reply_markup=get_topup_menu()
        )
    
    await callback.answer()


@router.callback_query(F.data == "topup_custom")
async def topup_custom(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(
            "💰 Пополнение баланса\n\nВведите сумму от 1 до 50000₽:"
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "💰 Пополнение баланса\n\nВведите сумму от 1 до 50000₽:"
        )
    
    await state.set_state(TopUpState.waiting_for_amount)
    await callback.answer()


@router.callback_query(F.data.startswith("topup_"))
async def topup_amount(callback: CallbackQuery):
    if callback.data == "topup_custom":
        return
    
    try:
        amount = int(callback.data.split("_")[1])
    except:
        await callback.answer("❌ Неверная сумма")
        return
    
    from handlers.shop import show_payment_methods
    await show_payment_methods(callback, amount, is_topup=True)
    await callback.answer()


@router.message(TopUpState.waiting_for_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 1 or amount > 50000:
            await message.answer("❌ Сумма от 1 до 50000₽")
            return
        
        from handlers.shop import show_payment_methods
        await show_payment_methods(message, amount, is_topup=True)
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число")


@router.callback_query(F.data == "promo")
async def promo_start(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(
            "🎫 Промокод\n\nВведите промокод:",
            reply_markup=get_back_to_main_keyboard()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "🎫 Промокод\n\nВведите промокод:",
            reply_markup=get_back_to_main_keyboard()
        )
    
    await state.set_state(PromoState.waiting_for_code)
    await callback.answer()


@router.message(PromoState.waiting_for_code)
async def process_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    
    promo = get_promocode(code)
    if promo:
        if use_promocode(message.from_user.id, code):
            reward = promo.get('reward', 0)
            update_balance(message.from_user.id, reward)
            await message.answer(
                f"✅ Промокод активирован!\n\n💰 +{reward}₽ на баланс",
                reply_markup=get_main_menu(message.from_user.id)
            )
        else:
            await message.answer(
                "❌ Промокод уже использован или истек",
                reply_markup=get_main_menu(message.from_user.id)
            )
    else:
        await message.answer(
            "❌ Неверный промокод",
            reply_markup=get_main_menu(message.from_user.id)
        )
    
    await state.clear()


@router.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery):
    purchases = get_user_purchases(callback.from_user.id)
    text = "⭐ История покупок ⭐\n\n"
    
    if not purchases:
        text = "📜 У вас пока нет покупок."
    else:
        for p in purchases[:10]:
            created_at = p.get('created_at', 'Неизвестно')
            if created_at and len(created_at) > 16:
                created_at = created_at[:16]
            
            text += f"🧾 Заказ #{p.get('order_number', 'N/A')}\n"
            text += f"   📦 {p.get('type', 'N/A').upper()}: {p.get('amount', 0)} - {p.get('price', 0)}₽\n"
            text += f"   📅 {created_at}\n"
            text += f"   ✅ Статус: {p.get('status', 'pending')}\n\n"
    
    try:
        await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_back_to_main_keyboard())
    
    await callback.answer()


@router.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery):
    from config import SUPPORT_ADMIN, SUPPORT_EMAIL
    
    support_admin = getattr(SUPPORT_ADMIN, '__str__', 'admin')
    support_email = getattr(SUPPORT_EMAIL, '__str__', 'support@example.com')
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Написать администратору", url=f"https://t.me/{support_admin}")],
            [InlineKeyboardButton(text="✉️ Написать на email", url=f"mailto:{support_email}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
        ]
    )
    
    try:
        await callback.message.edit_text(
            "📞 Служба поддержки\n\nСвяжитесь с нами:",
            reply_markup=keyboard
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "📞 Служба поддержки\n\nСвяжитесь с нами:",
            reply_markup=keyboard
        )
    
    await callback.answer()


@router.callback_query(F.data == "referral_info")
async def referral_info(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    referral_code = user.get('referral_code', '')
    bot_username = (await callback.bot.get_me()).username
    
    text = f"""👥 Реферальная система

Ваша статистика:
• Приглашено друзей: {user.get('referral_count', 0)}
• Заработано: {user.get('referral_earnings', 0)}₽

Бонусы:
• За каждого приглашенного: +{REFERRAL_BONUS}₽
• {REFERRAL_REWARD_PERCENT}% от покупок рефералов

Ваша реферальная ссылка:
https://t.me/{bot_username}?start={referral_code}

Отправьте эту ссылку другу! При переходе и регистрации вы получите бонус."""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Поделиться", switch_inline_query=referral_code)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()
    

