from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_all_tasks, get_user_task, create_user_task, update_user_task_status, get_user_completed_tasks
from keyboards.inline import get_back_to_main_keyboard
from config import get_premium_emoji, ADMIN_IDS

router = Router()


class TaskProofState(StatesGroup):
    waiting_for_proof = State()


@router.callback_query(F.data == "tasks_section")
async def show_tasks(callback: CallbackQuery):
    tasks = get_all_tasks()
    if not tasks:
        await callback.message.edit_text("📋 Нет доступных заданий", reply_markup=get_back_to_main_keyboard())
        return
    
    text = f"{get_premium_emoji()} <b>Доступные задания</b>\n\n"
    buttons = []
    for task in tasks:
        user_task = get_user_task(callback.from_user.id, task['id'])
        status = "✅" if user_task and user_task['status'] == 'approved' else "🆕" if not user_task else "⏳"
        text += f"{status} <b>{task['title']}</b>\n"
        text += f"📝 {task['description']}\n"
        text += f"💰 Награда: {task['reward']}₽\n\n"
        buttons.append([InlineKeyboardButton(text=f"{task['title']} +{task['reward']}₽", callback_data=f"task_{task['id']}")])
    
    buttons.append([InlineKeyboardButton(text="📋 Мои задания", callback_data="my_tasks")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    
    from aiogram.types import InlineKeyboardMarkup
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("task_") and not F.data.startswith("task_start_"))
async def show_task_detail(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    tasks = get_all_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        await callback.answer("Задание не найдено")
        return
    
    user_task = get_user_task(callback.from_user.id, task_id)
    status = user_task['status'] if user_task else None
    status_text = "✅ Выполнено" if status == 'approved' else "⏳ На проверке" if status == 'pending' else "❌ Отклонено" if status == 'rejected' else "🆕 Не начато"
    
    text = f"""{get_premium_emoji()} <b>{task['title']}</b>\n\n"
    f"📝 {task['description']}\n"
    f"💰 Награда: {task['reward']}₽\n"
    f"🔗 Цель: {task['target']}\n\n"
    f"📊 Статус: {status_text}"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [] if status is not None else [InlineKeyboardButton(text="✅ Начать выполнение", callback_data=f"task_start_{task_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_section")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("task_start_"))
async def start_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[2])
    tasks = get_all_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        await callback.answer("Задание не найдено")
        return
    
    existing = get_user_task(callback.from_user.id, task_id)
    if existing and existing['status'] in ['pending', 'approved']:
        await callback.answer("Вы уже выполнили это задание")
        return
    
    create_user_task(callback.from_user.id, task_id)
    
    text = f"""{get_premium_emoji()} <b>{task['title']}</b>\n\n"
    f"📝 {task['description']}\n\n"
    f"📌 Инструкция: {task['target']}\n\n"
    f"✏️ Отправьте подтверждение выполнения:\n"
    f"• 📸 Скриншот (фото)\n"
    f"• 🔗 Ссылка\n"
    f"• 📝 Текстовое описание\n\n"
    f"🚀 Для отмены отправьте /cancel"""
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(TaskProofState.waiting_for_proof)
    await state.update_data(task_id=task_id)
    await callback.answer()


@router.message(TaskProofState.waiting_for_proof)
async def process_task_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get('task_id')
    
    if not task_id:
        await message.answer("❌ Ошибка: задание не найдено")
        await state.clear()
        return
    
    proof = None
    if message.photo:
        proof = "📸 Фото отправлено"
    elif message.text:
        proof = message.text
    else:
        await message.answer("❌ Отправьте текст или фото")
        return
    
    update_user_task_status(message.from_user.id, task_id, 'pending', proof)
    
    tasks = get_all_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    text = f"""{get_premium_emoji()} <b>Задание отправлено на проверку!</b>\n\n"
    f"Статус: ⏳ Ожидает проверки\n"
    f"💰 Награда: {task['reward'] if task else 0}₽\n\n"
    f"✨ После подтверждения награда будет зачислена"""
    
    await message.answer(text, parse_mode="HTML")
    await state.clear()
    
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"🆕 <b>Новое задание на проверку!</b>\n\n"
                f"👤 {message.from_user.full_name}\n"
                f"📋 {task['title'] if task else 'Unknown'}\n"
                f"📝 {proof[:200]}",
                parse_mode="HTML"
            )
        except:
            pass


@router.callback_query(F.data == "my_tasks")
async def show_my_tasks(callback: CallbackQuery):
    tasks = get_user_completed_tasks(callback.from_user.id)
    
    if not tasks:
        text = "📋 У вас пока нет выполненных заданий."
    else:
        text = f"{get_premium_emoji()} <b>Мои задания</b>\n\n"
        total = 0
        for task in tasks:
            if task['status'] == 'approved':
                total += task['reward']
                text += f"✅ <b>{task['title']}</b> +{task['reward']}₽\n"
            else:
                text += f"⏳ <b>{task['title']}</b> (на проверке)\n"
        text += f"\n💰 <b>Всего заработано:</b> {total}₽"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()
