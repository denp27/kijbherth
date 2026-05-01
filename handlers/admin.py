# handlers/admin.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database import get_all_users, get_user, ban_user, unban_user, update_balance, get_stats, add_promocode, get_user_purchases
from keyboards import get_admin_menu, get_admin_users_list, get_admin_user_actions, get_mailing_keyboard, get_mailing_confirm_keyboard, get_admin_prices_keyboard, get_back_to_main_keyboard
from config import ADMIN_IDS, STARS_PRICES, PREMIUM_PRICES

router = Router()


class MailingState(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirmation = State()


class PromoState(StatesGroup):
    waiting_for_code = State()
    waiting_for_reward = State()
    waiting_for_uses = State()


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    stats = get_stats()
    text = f"""🔧 Админ панель

👥 Пользователей: {stats['total_users']}
💰 Выручка: {stats['total_revenue']}₽
📦 Покупок: {stats['total_purchases']}
⭐ Stars: {stats['total_stars_sold']}
💎 Premium: {stats['total_premium_sold']}
👥 Реферальных выплат: {stats['total_referral_paid']}₽
📈 Выручка сегодня: {stats['today_revenue']}₽"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_menu())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_admin_menu())
    
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, page: int = 0):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    users = get_all_users()
    
    try:
        await callback.message.edit_text(
            "👥 Список пользователей",
            reply_markup=get_admin_users_list(users, page)
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "👥 Список пользователей",
            reply_markup=get_admin_users_list(users, page)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users_page_"))
async def admin_users_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[3])
    await admin_users(callback, page)


@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_detail(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[2])
    user = get_user(user_id)
    
    registered_at = user.get('registered_at', 'Неизвестно')
    if registered_at and len(registered_at) > 10:
        registered_at = registered_at[:10]
    
    text = f"""👤 Информация о пользователе

🆔 ID: {user['user_id']}
👤 Имя: {user.get('first_name') or user.get('username') or 'Без имени'}
💰 Баланс: {user.get('balance', 0)}₽
👥 Рефералов: {user.get('referral_count', 0)}
🎁 Заработано: {user.get('referral_earnings', 0)}₽
📅 Регистрация: {registered_at}
🚫 Статус: {'🔴 Забанен' if user.get('is_banned') else '🟢 Активен'}"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_user_actions(user_id, user.get('is_banned', False)))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_admin_user_actions(user_id, user.get('is_banned', False)))
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[2])
    user = get_user(user_id)
    
    if user.get('is_banned'):
        unban_user(user_id)
        await callback.answer("✅ Пользователь разбанен")
    else:
        ban_user(user_id)
        await callback.answer("🔒 Пользователь забанен")
    
    await admin_user_detail(callback)


class AddBalanceState(StatesGroup):
    waiting_for_amount = State()


@router.callback_query(F.data.startswith("admin_add_balance_"))
async def admin_add_balance(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[3])
    await state.update_data(balance_user_id=user_id)
    await callback.message.answer("💰 Введите сумму для пополнения (в рублях):")
    await state.set_state(AddBalanceState.waiting_for_amount)
    await callback.answer()


@router.message(AddBalanceState.waiting_for_amount)
async def process_admin_balance(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data()
        user_id = data['balance_user_id']
        update_balance(user_id, amount)
        await message.answer(f"✅ Начислено {amount}₽ пользователю", reply_markup=get_admin_menu())
    except ValueError:
        await message.answer("❌ Введите число")
    await state.clear()


@router.callback_query(F.data.startswith("admin_user_history_"))
async def admin_user_history(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[3])
    user = get_user(user_id)
    purchases = get_user_purchases(user_id, 10)
    
    if not purchases:
        text = "📜 Нет покупок"
    else:
        text = "📜 История покупок\n\n"
        for p in purchases:
            created_at = p.get('created_at', 'Неизвестно')
            if created_at and len(created_at) > 10:
                created_at = created_at[:10]
            text += f"• Заказ #{p.get('order_number', 'N/A')}: {p.get('type', 'N/A').upper()} - {p.get('price', 0)}₽ ({created_at})\n"
    
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_user_actions(user_id, user.get('is_banned', False)))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_admin_user_actions(user_id, user.get('is_banned', False)))
    
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    stats = get_stats()
    text = f"""📊 Статистика

👥 Пользователей: {stats['total_users']}
💰 Выручка: {stats['total_revenue']}₽
📦 Покупок: {stats['total_purchases']}
⭐ Stars: {stats['total_stars_sold']}
💎 Premium: {stats['total_premium_sold']}
👥 Реферальных выплат: {stats['total_referral_paid']}₽
📈 Выручка сегодня: {stats['today_revenue']}₽"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_menu())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_admin_menu())
    
    await callback.answer()


@router.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    try:
        await callback.message.edit_text(
            "📨 Рассылка\n\nВыберите тип:",
            reply_markup=get_mailing_keyboard()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "📨 Рассылка\n\nВыберите тип:",
            reply_markup=get_mailing_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "mailing_text")
async def mailing_text(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.answer(
        "📝 Отправьте текст рассылки\n\n"
        "Текст будет отправлен всем пользователям."
    )
    await state.set_state(MailingState.waiting_for_content)
    await state.update_data(mailing_type="text")
    await callback.answer()


@router.callback_query(F.data == "mailing_media")
async def mailing_media(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.answer(
        "🖼️ Отправьте медиафайл (фото или видео)\n\n"
        "Подпись к медиа будет отправлена вместе с файлом."
    )
    await state.set_state(MailingState.waiting_for_content)
    await state.update_data(mailing_type="media")
    await callback.answer()


@router.message(MailingState.waiting_for_content)
async def process_mailing_content(message: Message, state: FSMContext):
    data = await state.get_data()
    content = {"type": data['mailing_type']}
    
    if data['mailing_type'] == "text":
        if not message.text:
            await message.answer("❌ Отправьте текст")
            return
        content["text"] = message.text
    else:
        if message.photo:
            content["media_type"] = "photo"
            content["file_id"] = message.photo[-1].file_id
            content["caption"] = message.caption or ""
        elif message.video:
            content["media_type"] = "video"
            content["file_id"] = message.video.file_id
            content["caption"] = message.caption or ""
        else:
            await message.answer("❌ Отправьте фото или видео")
            return
    
    await state.update_data(content=content)
    
    preview = content.get('text', content.get('caption', 'Медиа файл'))[:300]
    await message.answer(
        f"📨 Предпросмотр рассылки\n\n{preview}\n\nОтправить всем пользователям?",
        reply_markup=get_mailing_confirm_keyboard()
    )
    await state.set_state(MailingState.waiting_for_confirmation)


@router.callback_query(F.data == "mailing_send")
async def mailing_send(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    data = await state.get_data()
    content = data.get('content')
    
    if not content:
        await callback.answer("❌ Ошибка: нет контента")
        return
    
    await callback.message.edit_text("🔄 Начинаю рассылку...")
    
    users = get_all_users()
    sent = 0
    failed = 0
    
    for user in users:
        if user.get('is_banned'):
            continue
        try:
            if content['type'] == "text":
                await callback.bot.send_message(user['user_id'], content['text'])
            else:
                if content['media_type'] == "photo":
                    await callback.bot.send_photo(user['user_id'], content['file_id'], caption=content.get('caption'))
                elif content['media_type'] == "video":
                    await callback.bot.send_video(user['user_id'], content['file_id'], caption=content.get('caption'))
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)
    
    await callback.message.edit_text(
        f"📨 Рассылка завершена!\n\n"
        f"✅ Успешно: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего пользователей: {len(users)}",
        reply_markup=get_admin_menu()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "mailing_cancel")
async def mailing_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена", reply_markup=get_admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_promocodes")
async def admin_promocodes(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.answer(
        "🎟️ Создание промокода\n\nВведите код промокода (буквы и цифры):"
    )
    await state.set_state(PromoState.waiting_for_code)
    await callback.answer()


@router.message(PromoState.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.update_data(code=code)
    await message.answer("💰 Введите сумму награды (рубли):")
    await state.set_state(PromoState.waiting_for_reward)


@router.message(PromoState.waiting_for_reward)
async def process_promo_reward(message: Message, state: FSMContext):
    try:
        reward = float(message.text.replace(",", "."))
        await state.update_data(reward=reward)
        await message.answer("🔢 Введите максимальное количество использований:")
        await state.set_state(PromoState.waiting_for_uses)
    except ValueError:
        await message.answer("❌ Введите число")


@router.message(PromoState.waiting_for_uses)
async def process_promo_uses(message: Message, state: FSMContext):
    try:
        uses = int(message.text)
        data = await state.get_data()
        
        from datetime import datetime, timedelta
        add_promocode(data['code'], data['reward'], uses, datetime.now() + timedelta(days=365))
        
        await message.answer(
            f"✅ Промокод создан!\n\n"
            f"🎟️ Код: {data['code']}\n"
            f"💰 Награда: {data['reward']}₽\n"
            f"🔢 Макс. использований: {uses}\n"
            f"📅 Действует: 1 год",
            reply_markup=get_admin_menu()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число")


@router.callback_query(F.data == "admin_prices")
async def admin_prices(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    text = "⚙️ Управление ценами\n\n⭐ Stars:\n"
    for stars, price in STARS_PRICES.items():
        text += f"• {stars} ⭐ - {price}₽\n"
    
    text += f"\n💎 Premium:\n"
    for months, price in PREMIUM_PRICES.items():
        text += f"• {months} мес - {price}₽\n"
    
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_prices_keyboard())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_admin_prices_keyboard())
    
    await callback.answer()


class EditStarsState(StatesGroup):
    waiting_for_prices = State()


class EditPremiumState(StatesGroup):
    waiting_for_prices = State()


@router.callback_query(F.data == "admin_edit_stars")
async def admin_edit_stars(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.answer(
        "⭐ Изменение цен на Stars\n\n"
        "Введите новые цены в формате:\n"
        "количество:цена количество:цена\n\n"
        "Пример:\n"
        "50:69 100:119 250:249"
    )
    await state.set_state(EditStarsState.waiting_for_prices)
    await callback.answer()


@router.message(EditStarsState.waiting_for_prices)
async def process_edit_stars(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        for part in parts:
            if ':' in part:
                stars, price = part.split(':')
                STARS_PRICES[int(stars)] = int(price)
        await message.answer("✅ Цены на Stars обновлены!", reply_markup=get_admin_menu())
    except:
        await message.answer("❌ Неверный формат. Пример: 50:69 100:119")
    await state.clear()


@router.callback_query(F.data == "admin_edit_premium")
async def admin_edit_premium(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.answer(
        "💎 Изменение цен на Premium\n\n"
        "Введите новые цены в формате:\n"
        "месяцы:цена месяцы:цена\n\n"
        "Пример:\n"
        "3:349 6:549 12:849"
    )
    await state.set_state(EditPremiumState.waiting_for_prices)
    await callback.answer()


@router.message(EditPremiumState.waiting_for_prices)
async def process_edit_premium(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        for part in parts:
            if ':' in part:
                months, price = part.split(':')
                PREMIUM_PRICES[int(months)] = int(price)
        await message.answer("✅ Цены на Premium обновлены!", reply_markup=get_admin_menu())
    except:
        await message.answer("❌ Неверный формат. Пример: 3:349 6:549")
    await state.clear()
