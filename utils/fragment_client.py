# utils/fragment_client.py
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class FragmentClient:
    def __init__(self):
        self.is_initialized = False

    async def init_client(self):
        self.is_initialized = True
        logger.info("Fragment client initialized")
        return True

    async def purchase_stars(self, username: str, amount: int) -> dict:
        logger.info(f"Purchasing {amount} stars for {username}")
        return {"success": True, "transaction_id": f"mock_tx_{username}_{amount}"}

    async def purchase_premium(self, username: str, months: int) -> dict:
        logger.info(f"Purchasing {months} months premium for {username}")
        return {"success": True, "transaction_id": f"mock_tx_{username}_{months}"}


# Создаем глобальный экземпляр
fragment_client = FragmentClient()


# ДОБАВЛЕННЫЕ ФУНКЦИИ:

def get_fragment_client() -> Optional[FragmentClient]:
    """Получить экземпляр Fragment клиента"""
    return fragment_client


def get_fragment_service() -> Optional[FragmentClient]:
    """Алиас для get_fragment_client для совместимости"""
    return fragment_client


def init_fragment_service(seed: str = None, api_key: str = None, cookies: dict = None) -> FragmentClient:
    """Инициализация Fragment сервиса"""
    global fragment_client
    if fragment_client is None:
        fragment_client = FragmentClient()
    return fragment_client


async def purchase_stars(username: str, amount: int) -> Dict[str, Any]:
    """Утилитарная функция для покупки Stars"""
    client = get_fragment_client()
    if not client:
        return {
            'success': False,
            'error': 'Fragment клиент не инициализирован',
            'message': '❌ Сервис покупки временно недоступен'
        }
    
    try:
        result = await client.purchase_stars(username, amount)
        return result
    except Exception as e:
        logger.error(f"Error purchasing stars: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'❌ Ошибка при покупке Stars: {str(e)}'
        }


async def purchase_premium(username: str, months: int) -> Dict[str, Any]:
    """Утилитарная функция для покупки Premium"""
    client = get_fragment_client()
    if not client:
        return {
            'success': False,
            'error': 'Fragment клиент не инициализирован',
            'message': '❌ Сервис покупки временно недоступен'
        }
    
    try:
        result = await client.purchase_premium(username, months)
        return result
    except Exception as e:
        logger.error(f"Error purchasing premium: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'❌ Ошибка при покупке Premium: {str(e)}'
        }
