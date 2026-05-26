from seekflow.models import ProviderConfig
from seekflow.providers.base import SearchProvider


class ProviderRegistry:
    _providers: dict[str, type[SearchProvider]] = {}

    @classmethod
    def register(cls, provider_class: type[SearchProvider]) -> type[SearchProvider]:
        cls._providers[provider_class.name] = provider_class
        return provider_class

    @classmethod
    def get(cls, name: str, config: ProviderConfig) -> SearchProvider:
        try:
            provider_class = cls._providers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown provider: {name}") from exc
        return provider_class(config)

    @classmethod
    def list_names(cls) -> list[str]:
        return sorted(cls._providers)
