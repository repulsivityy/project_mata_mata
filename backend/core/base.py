import aiohttp
from abc import ABC, abstractmethod
from typing import Optional
from backend.core.models import ScanResult

class BaseChecker(ABC):
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    @abstractmethod
    async def check(self, value: str, item_type: str) -> ScanResult:
        pass
