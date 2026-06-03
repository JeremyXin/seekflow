from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from seekflow.cli import app, run_repl


runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "seekflow 0.1.0" in result.stdout


def test_help_renders_root_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout


@pytest.mark.asyncio
async def test_run_repl_search_does_not_clear_latest_chat(mocker, app_config, tmp_path) -> None:
    app_config.llm.api_key = "test-key"
    saved = []

    async def fake_stream_chat_reply(text, history, config):
        yield "chat answer"

    class FakePipeline:
        async def run(self, text, config, on_chunk, on_sources):
            on_chunk("search answer")
            return SimpleNamespace(answer="search answer", sources=[], file_path=None)

    class FakeTUI:
        def __init__(
            self,
            config,
            history_path,
            messages,
            command_handler,
            chat_handler,
            search_handler,
            get_mode,
            set_mode,
        ) -> None:
            self.messages = messages
            self.command_handler = command_handler
            self.chat_handler = chat_handler
            self.search_handler = search_handler

        def refresh(self) -> None:
            return None

        def schedule_refresh(self) -> None:
            return None

        async def run(self) -> None:
            await self.chat_handler("hello")
            await self.search_handler("python news")
            await self.command_handler("/save")

    async def fake_save_entry(entry, kb_dir, obsidian_mode=False):
        saved.append(entry)
        return tmp_path / "saved-chat.md"

    mocker.patch("seekflow.cli.SearchPipeline", return_value=FakePipeline())
    mocker.patch("seekflow.cli.stream_chat_reply", side_effect=fake_stream_chat_reply)
    mocker.patch("seekflow.cli.SeekFlowTUI", FakeTUI)
    mocker.patch("seekflow.repl.commands.save_entry", side_effect=fake_save_entry)

    await run_repl(app_config)

    assert len(saved) == 1
    assert saved[0].query == "hello"
