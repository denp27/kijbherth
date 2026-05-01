import logging

logger = logging.getLogger(__name__)


class CryptoBotClient:
    def __init__(self):
        self.is_initialized = False

    async def init_client(self):
        self.is_initialized = True
        logger.info("CryptoBot client initialized")
        return True


class PlategaClient:
    def __init__(self):
        self.is_initialized = False

    async def init_client(self):
        self.is_initialized = True
        logger.info("Platega client initialized")
        return True


cryptobot_client = CryptoBotClient()
platega_client = PlategaClient()
