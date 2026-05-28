import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from seekflow.config import get_default_config
from seekflow.models import ConversationTurn


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class SimpleMocker:
    def __init__(self) -> None:
        self._patches: list[patch] = []

    def patch(self, target: str, *args, **kwargs):
        active = patch(target, *args, **kwargs)
        mocked = active.start()
        self._patches.append(active)
        return mocked

    def stopall(self) -> None:
        while self._patches:
            self._patches.pop().stop()


@pytest.fixture
def mocker():
    helper = SimpleMocker()
    try:
        yield helper
    finally:
        helper.stopall()


@pytest.fixture
def app_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SEEKFLOW_CONFIG_PATH", str(tmp_path / ".seekflow" / "config.toml"))
    return get_default_config(home_dir=tmp_path)


@pytest.fixture
def conversation_history():
    return [
        ConversationTurn(role="user", content="hello"),
        ConversationTurn(role="assistant", content="hi"),
    ]
