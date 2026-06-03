from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class SearchResult:
    url: str
    title: str
    snippet: str
    content: str | None = None
    provider: str = ""


@dataclass(slots=True)
class KBEntry:
    title: str
    date: datetime
    query: str
    answer: str
    tags: list[str]
    category: str
    provider: str
    model: str
    summary: str
    sources: list[SearchResult] = field(default_factory=list)
    file_path: Path | None = None


@dataclass(slots=True)
class ProviderConfig:
    enabled: bool = False
    api_key: str | None = None
    browser: str = "chromium"
    headless: bool = False


@dataclass(slots=True)
class LLMConfig:
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"


@dataclass(slots=True)
class AppRuntimeConfig:
    default_provider: str = "duckduckgo"
    max_results: int = 5
    extract_top_n: int = 3


@dataclass(slots=True)
class KnowledgeBaseConfig:
    kb_dir: Path
    obsidian_mode: bool = False
    obsidian_vault_path: Path | None = None
    obsidian_subfolder: str = "SeekFlow"


@dataclass(slots=True)
class AppConfig:
    llm: LLMConfig
    app: AppRuntimeConfig
    knowledge_base: KnowledgeBaseConfig
    providers: dict[str, ProviderConfig]

@dataclass(slots=True)
class ConversationTurn:
    role: str
    content: str
