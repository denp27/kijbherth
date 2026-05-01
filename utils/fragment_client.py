import logging

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


fragment_client = FragmentClient()
