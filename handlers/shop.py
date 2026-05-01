# handlers/shop.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database import get_user, get_balance, deduct_balance, add_purchase
from keyboards.inline import get_back_to_main_keyboard, get_main_menu
from config import ADMIN_IDS
from utils.fragment_client import get_fragment_service

router = Router()


class GiftState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_item = State()


def get_stars_price(amount: int) -> float:
    """Цены Stars в рублях"""
    prices = {50: 59, 100: 99, 250: 229, 500: 429, 1000: 799, 2500: 1899, 5000: 3599}
    return prices.get(amount, amount)


def get_premium_price(months: int) -> float:
    """Цены Premium в рублях"""
    prices = {3: 299, 6: 499, 12: 799}
    return prices.get(months, months * 100)


@router.callback_query(F.data == "shop")
async def show_shop(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    balance = user.get('balance', 0) if user else 0
    
    text = f"🛍 Магазин\n\n💰 Ваш баланс: {balance}₽\n\nВыберите категорию:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="buy_stars")],
        [InlineKeyboardButton(text="💎 Купить Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🎁 Подарок другу", callback_data="gift_menu")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "buy_stars")
async def buy_stars(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 Stars - 59₽", callback_data="stars_50")],
        [InlineKeyboardButton(text="100 Stars - 99₽", callback_data="stars_100")],
        [InlineKeyboardButton(text="250 Stars - 229₽", callback_data="stars_250")],
        [InlineKeyboardButton(text="500 Stars - 429₽", callback_data="stars_500")],
        [InlineKeyboardButton(text="1000 Stars - 799₽", callback_data="stars_1000")],
        [InlineKeyboardButton(text="2500 Stars - 1899₽", callback_data="stars_2500")],
        [InlineKeyboardButton(text="5000 Stars - 3599₽", callback_data="stars_5000")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
    ])
    
    await callback.message.edit_text("⭐ Покупка Stars\n\nВыберите количество:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="3 месяца - 299₽", callback_data="premium_3")],
        [InlineKeyboardButton(text="6 месяцев - 499₽", callback_data="premium_6")],
        [InlineKeyboardButton(text="12 месяцев - 799₽", callback_data="premium_12")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
    ])
    
    await callback.message.edit_text("💎 Покупка Premium подписки\n\nВыберите срок:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("stars_"))
async def buy_stars_item(callback: CallbackQuery):
    amount = int(callback.data.split("_")[1])
    price = get_stars_price(amount)
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    username = user.get('username')
    if not username:
        await callback.message.edit_text(
            "❌ У вас не установлен username в Telegram!\n\n"
            "Пожалуйста, установите username в настройках Telegram.",
            reply_markup=get_back_to_main_keyboard()
        )
        await callback.answer()
        return
    
    balance = get_balance(user_id)
    if balance < price:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
        ])
        await callback.message.edit_text(
            f"❌ Недостаточно средств!\n\nНужно: {price}₽\nВаш баланс: {balance}₽",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    # Отправляем статус "обработка"
    await callback.message.edit_text(
        f"⏳ Отправка {amount} Stars пользователю @{username}...\n\n"
        f"Пожалуйста, подождите, операция может занять до 30 секунд."
    )
    
    # Покупка через Fragment
    fragment = get_fragment_service()
    if not fragment:
        await callback.message.edit_text(
            "❌ Сервис покупки временно недоступен. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )
        await callback.answer()
        return
    
    result = await fragment.purchase_stars(username, amount)
    
    if result['success']:
        # Списание средств
        deduct_balance(user_id, price)
        add_purchase(user_id, "stars", amount, price, "fragment", None, False)
        
        await callback.message.edit_text(
            f"✅ Покупка успешна!\n\n"
            f"⭐ Stars: {amount}\n"
            f"💰 Сумма: {price}₽\n"
            f"📦 Статус: Отправлено\n"
            f"🆔 Транзакция: {result.get('transaction_id', 'N/A')[:16]}...\n\n"
            f"Stars зачислены на аккаунт @{username}!",
            reply_markup=get_back_to_main_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка при покупке: {result.get('error', 'Неизвестная ошибка')}\n\n"
            f"Средства не были списаны. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("premium_"))
async def buy_premium_item(callback: CallbackQuery):
    months = int(callback.data.split("_")[1])
    price = get_premium_price(months)
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    username = user.get('username')
    if not username:
        await callback.message.edit_text(
            "❌ У вас не установлен username в Telegram!\n\n"
            "Пожалуйста, установите username в настройках Telegram.",
            reply_markup=get_back_to_main_keyboard()
        )
        await callback.answer()
        return
    
    balance = get_balance(user_id)
    if balance < price:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
        ])
        await callback.message.edit_text(
            f"❌ Недостаточно средств!\n\nНужно: {price}₽\nВаш баланс: {balance}₽",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"⏳ Оформление Premium на {months} месяцев для @{username}...\n\n"
        f"Пожалуйста, подождите, операция может занять до 30 секунд."
    )
    
    fragment = get_fragment_service()
    if not fragment:
        await callback.message.edit_text(
            "❌ Сервис покупки временно недоступен. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )
        await callback.answer()
        return
    
    result = await fragment.purchase_premium(username, months)
    
    if result['success']:
        deduct_balance(user_id, price)
        add_purchase(user_id, "premium", months, price, "fragment", None, False)
        
        await callback.message.edit_text(
            f"✅ Покупка успешна!\n\n"
            f"💎 Premium: {months} месяцев\n"
            f"💰 Сумма: {price}₽\n"
            f"📦 Статус: Активирован\n"
            f"🆔 Транзакция: {result.get('transaction_id', 'N/A')[:16]}...\n\n"
            f"Premium подписка активирована для @{username}!",
            reply_markup=get_back_to_main_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка при покупке: {result.get('error', 'Неизвестная ошибка')}\n\n"
            f"Средства не были списаны. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "gift_menu")
async def gift_menu(callback: CallbackQuery, state: FSMContext):
    text = """🎁 Подарок другу

Введите ID пользователя Telegram, которому хотите сделать подарок.

ID можно узнать у пользователя через команду /myid"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="shop")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    
    await state.set_state(GiftState.waiting_for_user_id)
    await callback.answer()


@router.message(GiftState.waiting_for_user_id)
async def process_gift_user(message: Message, state: FSMContext):
    try:
        gift_to_id = int(message.text.strip())
        
        if gift_to_id == message.from_user.id:
            await message.answer("❌ Нельзя сделать подарок самому себе!")
            return
        
        gift_user = get_user(gift_to_id)
        if not gift_user:
            await message.answer("❌ Пользователь с таким ID не найден!")
            return
        
        await state.update_data(gift_to_id=gift_to_id, gift_username=gift_user.get('username'))
        
        await message.answer(
            f"🎁 Выберите подарок для пользователя {gift_user.get('first_name', 'Пользователь')}:\n\n"
            f"1. Stars\n"
            f"2. Premium подписка\n\n"
            f"Напишите номер выбранного пункта:"
        )
        await state.set_state(GiftState.waiting_for_item)
        
    except ValueError:
        await message.answer("❌ Введите корректный ID (только цифры)")


@router.message(GiftState.waiting_for_item)
async def process_gift_item(message: Message, state: FSMContext):
    data = await state.get_data()
    gift_to_id = data.get('gift_to_id')
    gift_username = data.get('gift_username')
    gift_type = data.get('gift_type')
    
    choice = message.text.strip()
    
    if choice == "1" and not gift_type:
        await state.update_data(gift_type="stars")
        await message.answer(
            "⭐ Выберите количество Stars для подарка:\n\n"
            "1. 50 Stars - 59₽\n"
            "2. 100 Stars - 99₽\n"
            "3. 250 Stars - 229₽\n"
            "4. 500 Stars - 429₽\n"
            "5. 1000 Stars - 799₽\n"
            "6. 2500 Stars - 1899₽\n"
            "7. 5000 Stars - 3599₽\n\n"
            "Напишите номер выбранного пункта:"
        )
    elif choice == "2" and not gift_type:
        await state.update_data(gift_type="premium")
        await message.answer(
            "💎 Выберите срок Premium подписки для подарка:\n\n"
            "1. 3 месяца - 299₽\n"
            "2. 6 месяцев - 499₽\n"
            "3. 12 месяцев - 799₽\n\n"
            "Напишите номер выбранного пункта:"
        )
    elif choice in ["1", "2", "3", "4", "5", "6", "7"] and gift_type == "stars":
        stars_options = {"1": 50, "2": 100, "3": 250, "4": 500, "5": 1000, "6": 2500, "7": 5000}
        amount = stars_options.get(choice)
        price = get_stars_price(amount)
        
        balance = get_balance(message.from_user.id)
        if balance < price:
            await message.answer(
                f"❌ Недостаточно средств!\n\nНужно: {price}₽\nВаш баланс: {balance}₽",
                reply_markup=get_main_menu(message.from_user.id)
            )
            await state.clear()
            return
        
        if not gift_username:
            await message.answer("❌ У получателя подарка не установлен username!")
            await state.clear()
            return
        
        await message.answer(f"⏳ Отправка {amount} Stars пользователю...")
        
        fragment = get_fragment_service()
        result = await fragment.purchase_stars(gift_username, amount)
        
        if result['success']:
            deduct_balance(message.from_user.id, price)
            add_purchase(message.from_user.id, "stars_gift", amount, price, "fragment", str(gift_to_id), True)
            
            try:
                await message.bot.send_message(
                    gift_to_id,
                    f"🎁 Поздравляем!\n\nПользователь {message.from_user.first_name} подарил вам {amount} Stars!"
                )
            except:
                pass
            
            await message.answer(
                f"✅ Подарок успешно отправлен!\n\n"
                f"⭐ Stars: {amount}\n"
                f"💰 Сумма: {price}₽\n"
                f"🆔 Транзакция: {result.get('transaction_id', 'N/A')[:16]}...\n\n"
                f"Пользователь получит уведомление.",
                reply_markup=get_main_menu(message.from_user.id)
            )
        else:
            await message.answer(
                f"❌ Ошибка при отправке подарка: {result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Средства не были списаны.",
                reply_markup=get_main_menu(message.from_user.id)
            )
        
        await state.clear()
        
    elif choice in ["1", "2", "3"] and gift_type == "premium":
        premium_options = {"1": 3, "2": 6, "3": 12}
        months = premium_options.get(choice)
        price = get_premium_price(months)
        
        balance = get_balance(message.from_user.id)
        if balance < price:
            await message.answer(
                f"❌ Недостаточно средств!\n\nНужно: {price}₽\nВаш баланс: {balance}₽",
                reply_markup=get_main_menu(message.from_user.id)
            )
            await state.clear()
            return
        
        if not gift_username:
            await message.answer("❌ У получателя подарка не установлен username!")
            await state.clear()
            return
        
        await message.answer(f"⏳ Оформление Premium на {months} месяцев...")
        
        fragment = get_fragment_service()
        result = await fragment.purchase_premium(gift_username, months)
        
        if result['success']:
            deduct_balance(message.from_user.id, price)
            add_purchase(message.from_user.id, "premium_gift", months, price, "fragment", str(gift_to_id), True)
            
            try:
                await message.bot.send_message(
                    gift_to_id,
                    f"🎁 Поздравляем!\n\nПользователь {message.from_user.first_name} подарил вам Premium подписку на {months} месяцев!"
                )
            except:
                pass
            
            await message.answer(
                f"✅ Подарок успешно отправлен!\n\n"
                f"💎 Premium: {months} месяцев\n"
                f"💰 Сумма: {price}₽\n"
                f"🆔 Транзакция: {result.get('transaction_id', 'N/A')[:16]}...\n\n"
                f"Пользователь получит уведомление.",
                reply_markup=get_main_menu(message.from_user.id)
            )
        else:
            await message.answer(
                f"❌ Ошибка при отправке подарка: {result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Средства не были списаны.",
                reply_markup=get_main_menu(message.from_user.id)
            )
        
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, выберите пункт из списка (1-7)")
