from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from database import get_user, get_referrals
from keyboards.inline import get_back_to_main_keyboard
from config import get_premium_emoji, REFERRAL_REWARD_PERCENT, REFERRAL_BONUS

router = Router()


@router.callback_query(F.data == "referral_info")
async def referral_info(callback: CallbackQuery):
    """Информация о реферальной программе"""
    user = get_user(callback.from_user.id)
    referrals = get_referrals(callback.from_user.id)
    
    text = f"""{get_premium_emoji()} <b>Реферальная программа</b> {get_premium_emoji()}

✨ <b>Как это работает:</b>
• Приглашайте друзей по вашей ссылке
• Вы получаете {REFERRAL_REWARD_PERCENT}% от суммы покупок ваших друзей
• Бонус {REFERRAL_BONUS}₽ за каждого приглашенного друга

📊 <b>Ваша статистика:</b>
👥 Приглашено друзей: {user['referral_count']}
💰 Заработано: {user['referral_earnings']}₽

👥 <b>Список рефералов:</b>
"""
    
    if referrals:
        for ref in referrals[:10]:
            text += f"• {ref['first_name'] or ref['username'] or ref['user_id']}\n"
            text += f"  📅 {ref['registered_at'][:10]}\n"
    else:
        text += "• Пока нет приглашенных друзей\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()
