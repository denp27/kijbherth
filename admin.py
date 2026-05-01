from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

from database import get_all_users, get_user, ban_user, unban_user, update_balance, get_stats, add_promocode, get_user_purchases
from keyboards.inline import get_admin_menu, get_admin_users_list, get_admin_user_actions, get_mailing_keyboard, get_mailing_confirm_keyboard, get_admin_prices_keyboard, get_back_to_main_keyboard
from config import ADMIN_IDS, STARS_PRICES, PREMIUM_PRICES, get_premium_emoji

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
    text = f"""{get_premium_emoji()} <b>Админ панель</b> {get_premium_emoji()}

👥 Пользователей: {stats['total_users']}
💰 Выручка: {stats['total_revenue']}₽
📦 Покупок: {stats['total_purchases']}
⭐ Stars: {stats['total_stars_sold']}
💎 Premium: {stats['total_premium_sold']}
👥 Реферальных выплат: {stats['total_referral_paid']}₽
📈 Выручка сегодня: {stats['today_revenue']}₽"""
    
    await callback.message.edit_text(text, reply_markup=get_admin_menu(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, page: int = 0):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    users = get_all_users()
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Список пользователей</b>",
        reply_markup=get_admin_users_list(users, page),
        parse_mode="HTML"
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
    
    text = f"""{get_premium_emoji()} <b>Информация о пользователе</b> {get_premium_emoji()}

🆔 ID: <code>{user['user_id']}</code>
👤 Имя: {user['first_name'] or user['username'] or 'Без имени'}
💰 Баланс: {user['balance']}₽
👥 Рефералов: {user['referral_count']}
🎁 Заработано: {user['referral_earnings']}₽
📅 Регистрация: {user['registered_at'][:10] if user['registered_at'] else 'Неизвестно'}
🚫 Статус: {'🔴 Забанен' if user['is_banned'] else '🟢 Активен'}"""
    
    await callback.message.edit_text(text, reply_markup=get_admin_user_actions(user_id, user['is_banned']), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[2])
    user = get_user(user_id)
    
    if user['is_banned']:
        unban_user(user_id)
        await callback.answer("✅ Разбанен")
    else:
        ban_user(user_id)
        await callback.answer("🔒 Забанен")
    
    await admin_user_detail(callback)


@router.callback_query(F.data.startswith("admin_add_balance_"))
async def admin_add_balance(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[3])
    await state.update_data(balance_user_id=user_id)
    await callback.message.answer("💰 Введите сумму для пополнения:")
    await state.set_state(MailingState.waiting_for_content)
    await callback.answer()


@router.message(MailingState.waiting_for_content)
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
    purchases = get_user_purchases(user_id, 10)
    
    if not purchases:
        text = "📜 Нет покупок"
    else:
        text = f"{get_premium_emoji()} <b>История покупок</b>\n\n"
        for p in purchases:
            text += f"• Заказ #{p['order_number']}: {p['type'].upper()} - {p['price']}₽ ({p['created_at'][:10]})\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_user_actions(user_id, user['is_banned']), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    stats = get_stats()
    text = f"""{get_premium_emoji()} <b>Статистика</b> {get_premium_emoji()}

👥 Пользователей: {stats['total_users']}
💰 Выручка: {stats['total_revenue']}₽
📦 Покупок: {stats['total_purchases']}
⭐ Stars: {stats['total_stars_sold']}
💎 Premium: {stats['total_premium_sold']}
👥 Реферальных выплат: {stats['total_referral_paid']}₽
📈 Выручка сегодня: {stats['today_revenue']}₽"""
    
    await callback.message.edit_text(text, reply_markup=get_admin_menu(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Рассылка</b>\n\nВыберите тип:",
        reply_markup=get_mailing_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "mailing_text")
async def mailing_text(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.answer(
        "📝 <b>Отправьте текст рассылки</b>\n\n"
        "<b>Поддерживается HTML разметка:</b>\n"
        "• <code>&lt;b&gt;жирный&lt;/b&gt;</code>\n"
        "• <code>&lt;i&gt;курсив&lt;/i&gt;</code>\n"
        "• <code>&lt;tg-emoji emoji-id=\"ID\"&gt; &lt;/tg-emoji&gt;</code> - премиум эмодзи\n\n"
        "Пример с премиум эмодзи:\n"
        "<code>&lt;tg-emoji emoji-id=\"5471952986970267163\"&gt; &lt;/tg-emoji&gt; <b>Акция!</b></code>",
        parse_mode="HTML"
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
        "🖼️ <b>Отправьте медиафайл</b>\n\n"
        "Подпись поддерживает HTML форматирование и премиум эмодзи.\n\n"
        "Можно добавить инлайн кнопки (отдельным сообщением после медиа)",
        parse_mode="HTML"
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
            content["caption"] = message.caption
        elif message.video:
            content["media_type"] = "video"
            content["file_id"] = message.video.file_id
            content["caption"] = message.caption
        else:
            await message.answer("❌ Отправьте фото или видео")
            return
    
    await state.update_data(content=content)
    
    preview = content.get('text', content.get('caption', 'Медиа файл'))[:300]
    await message.answer(
        f"{get_premium_emoji()} <b>Предпросмотр рассылки</b>\n\n{preview}\n\nОтправить всем пользователям?",
        reply_markup=get_mailing_confirm_keyboard(),
        parse_mode="HTML"
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
        await callback.answer("Ошибка")
        return
    
    await callback.message.edit_text("🔄 Начинаю рассылку...")
    
    users = get_all_users()
    sent = 0
    failed = 0
    
    for user in users:
        if user['is_banned']:
            continue
        try:
            if content['type'] == "text":
                await callback.bot.send_message(user['user_id'], content['text'], parse_mode="HTML")
            else:
                if content['media_type'] == "photo":
                    await callback.bot.send_photo(user['user_id'], content['file_id'], caption=content.get('caption'), parse_mode="HTML")
                elif content['media_type'] == "video":
                    await callback.bot.send_video(user['user_id'], content['file_id'], caption=content.get('caption'), parse_mode="HTML")
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)
    
    await callback.message.edit_text(
        f"{get_premium_emoji()} <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего: {len(users)}",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "mailing_cancel")
async def mailing_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено", reply_markup=get_admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_promocodes")
async def admin_promocodes(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    from database import get_promocode
    
    await callback.message.answer(
        "🎟️ <b>Создание промокода</b>\n\n"
        "Введите код промокода (буквы и цифры):",
        parse_mode="HTML"
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
            f"✅ <b>Промокод создан!</b>\n\n"
            f"🎟️ Код: <code>{data['code']}</code>\n"
            f"💰 Награда: {data['reward']}₽\n"
            f"🔢 Макс. использований: {uses}\n"
            f"📅 Действует: 1 год",
            parse_mode="HTML",
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
    
    text = f"{get_premium_emoji()} <b>Управление ценами</b>\n\n⭐ <b>Stars:</b>\n"
    for stars, price in STARS_PRICES.items():
        text += f"• {stars} ⭐ - {price}₽\n"
    
    text += f"\n💎 <b>Premium:</b>\n"
    for months, price in PREMIUM_PRICES.items():
        text += f"• {months} мес - {price}₽\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_prices_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_edit_stars")
async def admin_edit_stars(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.answer(
        "⭐ <b>Изменение цен на Stars</b>\n\n"
        "Введите новые цены в формате:\n"
        "<code>количество:цена количество:цена</code>\n\n"
        "Пример:\n"
        "<code>50:69 100:119 250:249</code>",
        parse_mode="HTML"
    )
    await state.set_state(MailingState.waiting_for_content)
    await callback.answer()


@router.message(MailingState.waiting_for_content)
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
        "💎 <b>Изменение цен на Premium</b>\n\n"
        "Введите новые цены в формате:\n"
        "<code>месяцы:цена месяцы:цена</code>\n\n"
        "Пример:\n"
        "<code>3:349 6:549 12:849</code>",
        parse_mode="HTML"
    )
    await state.set_state(MailingState.waiting_for_content)
    await callback.answer()


@router.message(MailingState.waiting_for_content)
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
