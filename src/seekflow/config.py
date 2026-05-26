import os
import tomllib
from pathlib import Path

from tomlkit import document, dumps, table

from seekflow.models import AppConfig, AppRuntimeConfig, KnowledgeBaseConfig, LLMConfig, ProviderConfig


def get_config_path() -> Path:
    override = os.getenv("SEEKFLOW_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".seekflow" / "config.toml"


def get_default_config(home_dir: Path | None = None) -> AppConfig:
    base_home = home_dir or Path.home()
    seekflow_dir = base_home / ".seekflow"
    return AppConfig(
        llm=LLMConfig(),
        app=AppRuntimeConfig(),
        knowledge_base=KnowledgeBaseConfig(kb_dir=seekflow_dir / "knowledge"),
        providers={
            "duckduckgo": ProviderConfig(enabled=True),
            "brave": ProviderConfig(enabled=False),
            "serpapi": ProviderConfig(enabled=False),
            "playwright": ProviderConfig(enabled=False),
        },
    )


def _path_from_config_value(value: str) -> Path:
    return Path(value).expanduser()


def _apply_env_overrides(config: AppConfig) -> AppConfig:
    llm_api_key = os.getenv("SEEKFLOW_LLM_API_KEY")
    llm_base_url = os.getenv("SEEKFLOW_LLM_BASE_URL")
    llm_model = os.getenv("SEEKFLOW_LLM_MODEL")
    if llm_api_key is not None:
        config.llm.api_key = llm_api_key
    if llm_base_url is not None:
        config.llm.base_url = llm_base_url
    if llm_model is not None:
        config.llm.model = llm_model
    return config


def load_config(path: Path | None = None) -> AppConfig:
    path = path or get_config_path()
    if not path.exists():
        return _apply_env_overrides(get_default_config(path.parent.parent))

    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    defaults = get_default_config(path.parent.parent)
    llm_data = raw.get("llm", {})
    app_data = raw.get("app", {})
    kb_data = raw.get("knowledge_base", {})
    provider_data = raw.get("providers", {})

    config = AppConfig(
        llm=LLMConfig(
            api_key=llm_data.get("api_key", defaults.llm.api_key),
            base_url=llm_data.get("base_url", defaults.llm.base_url),
            model=llm_data.get("model", defaults.llm.model),
        ),
        app=AppRuntimeConfig(
            default_provider=app_data.get("default_provider", defaults.app.default_provider),
            max_results=app_data.get("max_results", defaults.app.max_results),
            extract_top_n=app_data.get("extract_top_n", defaults.app.extract_top_n),
        ),
        knowledge_base=KnowledgeBaseConfig(
            kb_dir=_path_from_config_value(str(kb_data.get("kb_dir", defaults.knowledge_base.kb_dir))),
            obsidian_mode=kb_data.get("obsidian_mode", defaults.knowledge_base.obsidian_mode),
            obsidian_vault_path=(
                _path_from_config_value(str(kb_data["obsidian_vault_path"]))
                if kb_data.get("obsidian_vault_path")
                else None
            ),
            obsidian_subfolder=kb_data.get("obsidian_subfolder", defaults.knowledge_base.obsidian_subfolder),
        ),
        providers={
            name: ProviderConfig(
                enabled=settings.get("enabled", defaults.providers[name].enabled),
                api_key=settings.get("api_key", defaults.providers[name].api_key),
                browser=settings.get("browser", defaults.providers[name].browser),
                headless=settings.get("headless", defaults.providers[name].headless),
            )
            for name, settings in {
                provider_name: provider_data.get(provider_name, {})
                for provider_name in defaults.providers
            }.items()
        },
    )
    return _apply_env_overrides(config)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    path = path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = document()

    llm_section = table()
    llm_section["api_key"] = config.llm.api_key
    llm_section["base_url"] = config.llm.base_url
    llm_section["model"] = config.llm.model
    doc["llm"] = llm_section

    app_section = table()
    app_section["default_provider"] = config.app.default_provider
    app_section["max_results"] = config.app.max_results
    app_section["extract_top_n"] = config.app.extract_top_n
    doc["app"] = app_section

    kb_section = table()
    kb_section["kb_dir"] = str(config.knowledge_base.kb_dir)
    kb_section["obsidian_mode"] = config.knowledge_base.obsidian_mode
    kb_section["obsidian_vault_path"] = (
        str(config.knowledge_base.obsidian_vault_path)
        if config.knowledge_base.obsidian_vault_path
        else ""
    )
    kb_section["obsidian_subfolder"] = config.knowledge_base.obsidian_subfolder
    doc["knowledge_base"] = kb_section

    providers_section = table()
    for name, provider in config.providers.items():
        provider_section = table()
        provider_section["enabled"] = provider.enabled
        if provider.api_key is not None:
            provider_section["api_key"] = provider.api_key
        if name == "playwright":
            provider_section["browser"] = provider.browser
            provider_section["headless"] = provider.headless
        providers_section[name] = provider_section
    doc["providers"] = providers_section

    path.write_text(dumps(doc))
    os.chmod(path, 0o600)
    return path


def ensure_config_exists(path: Path | None = None) -> Path:
    path = path or get_config_path()
    if path.exists():
        return path
    config = get_default_config(path.parent.parent)
    return save_config(config, path)
