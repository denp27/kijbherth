from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_user, create_user, update_balance, get_user_purchases, apply_promocode_reward, get_balance
from keyboards.inline import get_main_menu, get_topup_menu, get_back_to_main_keyboard
from config import REFERRAL_BONUS, REFERRAL_REWARD_PERCENT, get_premium_emoji, ADMIN_IDS

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
    
    if user.get('is_banned'):
        await message.answer("❌ Ваш аккаунт заблокирован.")
        return
    
    text = f"""{get_premium_emoji()} <b>Добро пожаловать в Telegram Stars & Premium Bot!</b> {get_premium_emoji()}

⭐ Здесь вы можете купить Telegram Stars и Premium подписку

💰 <b>Ваш баланс:</b> {user['balance']}₽

🚀 <b>Выберите действие:</b>"""
    
    await message.answer(text, reply_markup=get_main_menu(user_id), parse_mode="HTML")


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    user = get_user(message.from_user.id)
    text = f"""{get_premium_emoji()} <b>Главное меню</b> {get_premium_emoji()}

💰 <b>Ваш баланс:</b> {user['balance']}₽"""
    await message.answer(text, reply_markup=get_main_menu(message.from_user.id), parse_mode="HTML")


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user = get_user(message.from_user.id)
    await message.answer(f"{get_premium_emoji()} <b>Ваш баланс:</b> {user['balance']}₽", parse_mode="HTML")


@router.message(Command("myid"))
async def get_my_id(message: Message):
    await message.answer(f"✅ <b>Ваш ID:</b> <code>{message.from_user.id}</code>", parse_mode="HTML")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    text = f"""{get_premium_emoji()} <b>Главное меню</b> {get_premium_emoji()}

💰 <b>Ваш баланс:</b> {user['balance']}₽"""
    await callback.message.edit_text(text, reply_markup=get_main_menu(callback.from_user.id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    purchases = get_user_purchases(callback.from_user.id, 5)
    
    purchases_text = ""
    if purchases:
        for p in purchases[:3]:
            purchases_text += f"• Заказ #{p['order_number']}: {p['type'].upper()} - {p['price']}₽\n"
    else:
        purchases_text = "• Нет покупок"
    
    text = f"""{get_premium_emoji()} <b>Мой профиль</b> {get_premium_emoji()}

🆔 <b>ID:</b> <code>{user['user_id']}</code>
👤 <b>Имя:</b> {user['first_name'] or 'Без имени'}
💰 <b>Баланс:</b> {user['balance']}₽
💸 <b>Потрачено:</b> {user['total_spent']}₽
👥 <b>Рефералов:</b> {user['referral_count']}
🎁 <b>Заработано с рефералов:</b> {user['referral_earnings']}₽
📅 <b>Регистрация:</b> {user['registered_at'][:10]}

📜 <b>Последние покупки:</b>
{purchases_text}"""
    
    await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Ваш баланс:</b> {user['balance']}₽",
        reply_markup=get_back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "topup")
async def topup_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Пополнение баланса</b>\n\nВыберите сумму:",
        reply_markup=get_topup_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "topup_custom")
async def topup_custom(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Пополнение баланса</b>\n\nВведите сумму от 1 до 50000₽:",
        parse_mode="HTML"
    )
    await state.set_state(TopUpState.waiting_for_amount)
    await callback.answer()


@router.callback_query(F.data.startswith("topup_"))
async def topup_amount(callback: CallbackQuery):
    if callback.data == "topup_custom":
        return
    amount = int(callback.data.split("_")[1])
    
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
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Промокод</b>\n\nВведите промокод:",
        reply_markup=get_back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PromoState.waiting_for_code)
    await callback.answer()


@router.message(PromoState.waiting_for_code)
async def process_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    
    from database import get_promocode, use_promocode, apply_promocode_reward
    
    promo = get_promocode(code)
    if promo:
        if use_promocode(message.from_user.id, code):
            update_balance(message.from_user.id, promo['reward'])
            await message.answer(
                f"✅ <b>Промокод активирован!</b>\n\n"
                f"💰 +{promo['reward']}₽ на баланс",
                parse_mode="HTML",
                reply_markup=get_main_menu(message.from_user.id)
            )
        else:
            await message.answer("❌ Промокод уже использован или истек", reply_markup=get_main_menu(message.from_user.id))
    else:
        await message.answer("❌ Неверный промокод", reply_markup=get_main_menu(message.from_user.id))
    
    await state.clear()


@router.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery):
    purchases = get_user_purchases(callback.from_user.id)
    if not purchases:
        text = "📜 У вас пока нет покупок."
    else:
        text = f"{get_premium_emoji()} <b>История покупок</b> {get_premium_emoji()}\n\n"
        for p in purchases[:10]:
            text += f"🧾 <b>Заказ #{p['order_number']}</b>\n"
            text += f"   📦 {p['type'].upper()}: {p['amount']} - {p['price']}₽\n"
            text += f"   📅 {p['created_at'][:16]}\n"
            text += f"   ✅ Статус: {p['status']}\n\n"
    await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery):
    from config import SUPPORT_ADMIN, SUPPORT_EMAIL
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Написать администратору", url=f"https://t.me/{SUPPORT_ADMIN}")],
            [InlineKeyboardButton(text="✉️ Написать на email", url=f"mailto:{SUPPORT_EMAIL}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
        ]
    )
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Служба поддержки</b> {get_premium_emoji()}\n\nСвяжитесь с нами:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()
