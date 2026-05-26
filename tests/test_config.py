from pathlib import Path

from seekflow.config import get_default_config, load_config


def test_default_config_uses_duckduckgo(tmp_path: Path) -> None:
    config = get_default_config(home_dir=tmp_path)
    assert config.app.default_provider == "duckduckgo"
    assert config.knowledge_base.kb_dir == tmp_path / ".seekflow" / "knowledge"


def test_env_overrides_take_precedence(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[llm]\napi_key='from-file'\nbase_url='https://api.openai.com/v1'\nmodel='gpt-4o-mini'\n"
    )
    monkeypatch.setenv("SEEKFLOW_LLM_API_KEY", "from-env")
    config = load_config(config_path)
    assert config.llm.api_key == "from-env"
