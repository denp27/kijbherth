# /app/handlers/tasks.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from database import (
    get_all_tasks, 
    get_user_task, 
    create_user_task, 
    update_user_task_status, 
    get_user_completed_tasks,
    get_task
)
from keyboards import tasks_keyboard, task_detail_keyboard, confirm_keyboard, back_keyboard
from config import ADMIN_IDS

router = Router()

# Состояния для FSM
class TaskStates(StatesGroup):
    waiting_for_proof = State()


# Исправленный фильтр - нужно разделить на несколько декораторов или использовать MagicFilter правильно
@router.callback_query(F.data.startswith("task_"))
async def handle_task_callback(callback: CallbackQuery):
    """Обработчик всех callback с task_"""
    data = callback.data
    
    # Пропускаем task_start_
    if data.startswith("task_start_"):
        return
    
    # Обрабатываем другие task_ колбэки
    task_id = int(data.split("_")[1])
    user_id = callback.from_user.id
    
    task = get_task(task_id)
    if not task:
        await callback.answer("❌ Задание не найдено")
        await callback.message.edit_text("Задание не найдено")
        return
    
    user_task = get_user_task(user_id, task_id)
    
    if user_task and user_task.get('status') == 'approved':
        await callback.answer("✅ Вы уже выполнили это задание!")
        return
    
    await callback.message.edit_text(
        f"📋 <b>{task['title']}</b>\n\n"
        f"{task['description']}\n\n"
        f"💰 Награда: {task['reward']}⭐\n"
        f"📊 Тип: {task['task_type']}\n\n"
        f"Нажмите «Начать», чтобы приступить к выполнению.",
        reply_markup=task_detail_keyboard(task_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_start_"))
async def start_task(callback: CallbackQuery):
    """Начать выполнение задания"""
    task_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    task = get_task(task_id)
    if not task:
        await callback.answer("❌ Задание не найдено")
        return
    
    # Создаем запись о начале выполнения
    create_user_task(user_id, task_id)
    
    # В зависимости от типа задания
    if task['task_type'] == 'join_channel':
        await callback.message.edit_text(
            f"📌 <b>{task['title']}</b>\n\n"
            f"1️⃣ Подпишитесь на канал: {task['target']}\n"
            f"2️⃣ После подписки нажмите «Проверить»\n\n"
            f"После проверки вы получите {task['reward']}⭐",
            reply_markup=confirm_keyboard(task_id)
        )
    elif task['task_type'] == 'visit_link':
        await callback.message.edit_text(
            f"🔗 <b>{task['title']}</b>\n\n"
            f"Перейдите по ссылке:\n{task['target']}\n\n"
            f"После выполнения нажмите «Проверить»",
            reply_markup=confirm_keyboard(task_id)
        )
    elif task['task_type'] == 'custom':
        await callback.message.edit_text(
            f"📝 <b>{task['title']}</b>\n\n"
            f"{task['description']}\n\n"
            f"Отправьте доказательство выполнения (скриншот или текст).",
            reply_markup=back_keyboard(task_id)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("task_check_"))
async def check_task(callback: CallbackQuery):
    """Проверка выполнения задания (для автоматических заданий)"""
    task_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    task = get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задание не найдено")
        return
    
    # Здесь должна быть логика проверки выполнения
    # Например, проверка подписки на канал
    if task['task_type'] == 'join_channel':
        # Проверяем подписку (нужно реализовать через Bot API)
        # Это пример:
        is_member = await check_subscription(callback.bot, user_id, task['target'])
        
        if is_member:
            # Отмечаем задание как выполненное
            update_user_task_status(user_id, task_id, 'completed')
            await callback.message.edit_text(
                f"✅ Задание выполнено!\n\n"
                f"Получено {task['reward']}⭐\n"
                f"Ожидайте проверки администратора.",
                reply_markup=None
            )
        else:
            await callback.answer("❌ Вы не подписались на канал!", show_alert=True)
    else:
        await callback.answer("Это задание требует ручной проверки", show_alert=True)


@router.callback_query(F.data.startswith("task_proof_"))
async def request_proof(callback: CallbackQuery, state: FSMContext):
    """Запрос доказательства для задания с ручной проверкой"""
    task_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    await state.update_data(task_id=task_id)
    await state.set_state(TaskStates.waiting_for_proof)
    
    await callback.message.edit_text(
        "📎 Отправьте доказательство выполнения задания.\n\n"
        "Это может быть скриншот, ссылка или текстовое описание.",
        reply_markup=back_keyboard(task_id)
    )
    await callback.answer()


@router.message(TaskStates.waiting_for_proof)
async def handle_proof(message: Message, state: FSMContext):
    """Обработка доказательства выполнения"""
    data = await state.get_data()
    task_id = data.get('task_id')
    user_id = message.from_user.id
    
    task = get_task(task_id)
    if not task:
        await message.answer("❌ Задание не найдено")
        await state.clear()
        return
    
    proof_text = message.text
    if message.photo:
        proof_text = f"Фото: {message.photo[-1].file_id}"
    elif message.document:
        proof_text = f"Файл: {message.document.file_id}"
    
    # Сохраняем доказательство
    update_user_task_status(user_id, task_id, 'pending', proof_text)
    
    # Уведомляем админов (если есть)
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"📝 <b>Новая заявка на задание!</b>\n\n"
                f"👤 Пользователь: {message.from_user.full_name}\n"
                f"🆔 ID: {user_id}\n"
                f"📋 Задание: {task['title']}\n"
                f"💰 Награда: {task['reward']}⭐\n"
                f"📎 Доказательство: {proof_text[:200]}\n\n"
                f"Для подтверждения используйте кнопки ниже:"
            )
            
            await message.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=task_approve_keyboard(task_id, user_id)
            )
        except:
            pass
    
    await message.answer(
        f"✅ Ваше доказательство отправлено на проверку!\n\n"
        f"Администратор рассмотрит заявку в ближайшее время.\n"
        f"После подтверждения вы получите {task['reward']}⭐",
        reply_markup=None
    )
    await state.clear()


@router.callback_query(F.data.startswith("task_approve_"))
async def approve_task_callback(callback: CallbackQuery):
    """Админ: подтверждение задания"""
    parts = callback.data.split("_")
    task_id = int(parts[2])
    user_id = int(parts[3]) if len(parts) > 3 else None
    
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав!")
        return
    
    from database import approve_task
    approve_task(user_id, task_id, callback.from_user.id)
    
    # Уведомляем пользователя
    task = get_task(task_id)
    try:
        await callback.bot.send_message(
            user_id,
            f"✅ <b>Задание подтверждено!</b>\n\n"
            f"📋 {task['title']}\n"
            f"💰 Вы получили {task['reward']}⭐\n\n"
            f"Благодарим за выполнение!"
        )
    except:
        pass
    
    await callback.message.edit_text(
        f"✅ Задание подтверждено!\n"
        f"Пользователю {user_id} начислено {task['reward']}⭐",
        reply_markup=None
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_reject_"))
async def reject_task_callback(callback: CallbackQuery):
    """Админ: отклонение задания"""
    parts = callback.data.split("_")
    task_id = int(parts[2])
    user_id = int(parts[3]) if len(parts) > 3 else None
    
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав!")
        return
    
    from database import reject_task
    reject_task(user_id, task_id, callback.from_user.id)
    
    # Уведомляем пользователя
    task = get_task(task_id)
    try:
        await callback.bot.send_message(
            user_id,
            f"❌ <b>Задание отклонено!</b>\n\n"
            f"📋 {task['title']}\n\n"
            f"К сожалению, ваше доказательство не подошло.\n"
            f"Попробуйте выполнить задание заново и отправить корректное доказательство."
        )
    except:
        pass
    
    await callback.message.edit_text(
        f"❌ Задание отклонено!\n"
        f"Пользователь {user_id} не получит награду.",
        reply_markup=None
    )
    await callback.answer()


@router.message(Command("tasks"))
async def show_tasks(message: Message):
    """Показать список заданий"""
    user_id = message.from_user.id
    tasks = get_all_tasks()
    
    if not tasks:
        await message.answer("📋 Пока нет доступных заданий.\n\nЗаходите позже!")
        return
    
    completed_tasks = get_user_completed_tasks(user_id)
    completed_ids = [t['id'] for t in completed_tasks]
    
    text = "📋 <b>Доступные задания</b>\n\n"
    
    for task in tasks:
        if task['id'] in completed_ids:
            status = "✅"
        else:
            user_task = get_user_task(user_id, task['id'])
            if user_task:
                status = "⏳"
            else:
                status = "🔘"
        
        text += f"{status} <b>{task['title']}</b> - {task['reward']}⭐\n"
        text += f"   {task['description'][:50]}...\n\n"
    
    await message.answer(text, reply_markup=tasks_keyboard(tasks, completed_ids))


# Функция для проверки подписки (нужно реализовать)
async def check_subscription(bot, user_id, channel):
    """Проверка подписки пользователя на канал"""
    try:
        # Убираем @ из имени канала если есть
        channel_username = channel.replace('@', '')
        member = await bot.get_chat_member(f"@{channel_username}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False


# Вспомогательная клавиатура для админов
def task_approve_keyboard(task_id: int, user_id: int):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"task_approve_{task_id}_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"task_reject_{task_id}_{user_id}")
        ]
    ])
    return keyboard
