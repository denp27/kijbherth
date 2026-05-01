from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import STARS_PRICES, PREMIUM_PRICES, get_premium_emoji
from database import get_user, deduct_balance, add_purchase, complete_purchase, get_balance, update_balance
from keyboards.inline import get_shop_menu, get_stars_packs, get_premium_packs, get_insufficient_balance_keyboard, get_payment_methods_keyboard, get_back_to_main_keyboard
from utils.payments import cryptobot_client, platega_client

router = Router()


async def show_payment_methods(message, amount, is_topup=False):
    """Показать методы оплаты для пополнения"""
    if is_topup:
        from database import add_balance_topup
        topup_id = add_balance_topup(message.from_user.id, amount, "pending")
        
        keyboard = get_payment_methods_keyboard(amount, topup_id)
        
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(
                f"{get_premium_emoji()} <b>Пополнение баланса</b>\n\n"
                f"💰 Сумма: {amount}₽\n\n"
                f"Выберите способ оплаты:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"{get_premium_emoji()} <b>Пополнение баланса</b>\n\n"
                f"💰 Сумма: {amount}₽\n\n"
                f"Выберите способ оплаты:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )


@router.callback_query(F.data == "shop")
async def shop_menu(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Магазин</b> {get_premium_emoji()}\n\n💰 Баланс: {user['balance']}₽",
        reply_markup=get_shop_menu(user['balance']),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "buy_stars")
async def buy_stars_menu(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Покупка Stars</b> {get_premium_emoji()}\n\n💰 Баланс: {user['balance']}₽",
        reply_markup=get_stars_packs(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "buy_premium")
async def buy_premium_menu(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Покупка Premium</b> {get_premium_emoji()}\n\n💰 Баланс: {user['balance']}₽",
        reply_markup=get_premium_packs(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stars_"))
async def process_stars(callback: CallbackQuery):
    stars = int(callback.data.split("_")[1])
    price = STARS_PRICES[stars]
    user = get_user(callback.from_user.id)

    if user['balance'] >= price:
        deduct_balance(callback.from_user.id, price)
        purchase_id = add_purchase(callback.from_user.id, "stars", stars, price, "balance")
        
        complete_purchase(purchase_id)
        new_balance = get_balance(callback.from_user.id)
        
        text = f"""{get_premium_emoji()} <b>Покупка успешно совершена!</b> {get_premium_emoji()}

⭐ {stars} Stars зачислены на ваш аккаунт
🧾 <b>Номер заказа:</b> <code>#{purchase_id}</code>
💰 <b>Сумма:</b> {price}₽
💰 <b>Остаток на балансе:</b> {new_balance}₽

🚀 Спасибо за покупку!"""
        
        await callback.message.edit_text(text, reply_markup=get_shop_menu(new_balance), parse_mode="HTML")
    else:
        text = f"""{get_premium_emoji()} <b>Недостаточно средств!</b>

⭐ {stars} Stars - {price}₽
💰 Ваш баланс: {user['balance']}₽

Не хватает: {price - user['balance']}₽"""
        await callback.message.edit_text(text, reply_markup=get_insufficient_balance_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("premium_"))
async def process_premium(callback: CallbackQuery):
    months = int(callback.data.split("_")[1])
    price = PREMIUM_PRICES[months]
    user = get_user(callback.from_user.id)

    if user['balance'] >= price:
        deduct_balance(callback.from_user.id, price)
        purchase_id = add_purchase(callback.from_user.id, "premium", months, price, "balance")
        
        complete_purchase(purchase_id)
        new_balance = get_balance(callback.from_user.id)
        
        text = f"""{get_premium_emoji()} <b>Покупка успешно совершена!</b> {get_premium_emoji()}

💎 Premium на {months} месяцев активирован
🧾 <b>Номер заказа:</b> <code>#{purchase_id}</code>
💰 <b>Сумма:</b> {price}₽
💰 <b>Остаток на балансе:</b> {new_balance}₽

🚀 Спасибо за покупку!"""
        
        await callback.message.edit_text(text, reply_markup=get_shop_menu(new_balance), parse_mode="HTML")
    else:
        text = f"""{get_premium_emoji()} <b>Недостаточно средств!</b>

💎 Premium {months} мес - {price}₽
💰 Ваш баланс: {user['balance']}₽

Не хватает: {price - user['balance']}₽"""
        await callback.message.edit_text(text, reply_markup=get_insufficient_balance_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pay_cryptobot_"))
async def pay_cryptobot(callback: CallbackQuery):
    """Оплата через CryptoBot"""
    parts = callback.data.split("_")
    topup_id = int(parts[2])
    amount = float(parts[3])
    
    from database import complete_balance_topup
    complete_balance_topup(topup_id, f"cryptobot_tx_{topup_id}")
    
    new_balance = get_balance(callback.from_user.id)
    
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Баланс успешно пополнен!</b>\n\n"
        f"💰 Сумма: +{amount}₽\n"
        f"💰 Текущий баланс: {new_balance}₽\n\n"
        f"🚀 Теперь вы можете покупать Stars и Premium!",
        reply_markup=get_back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_platega_"))
async def pay_platega(callback: CallbackQuery):
    """Оплата через Platega.io"""
    parts = callback.data.split("_")
    topup_id = int(parts[2])
    amount = float(parts[3])
    
    from database import complete_balance_topup
    complete_balance_topup(topup_id, f"platega_tx_{topup_id}")
    
    new_balance = get_balance(callback.from_user.id)
    
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Баланс успешно пополнен!</b>\n\n"
        f"💰 Сумма: +{amount}₽\n"
        f"💰 Текущий баланс: {new_balance}₽\n\n"
        f"🚀 Теперь вы можете покупать Stars и Premium!",
        reply_markup=get_back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
