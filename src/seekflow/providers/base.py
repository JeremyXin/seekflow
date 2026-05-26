from abc import ABC, abstractmethod

from seekflow.models import ProviderConfig, SearchResult


class SearchProvider(ABC):
    name: str

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    async def is_available(self) -> bool:
        raise NotImplementedError
