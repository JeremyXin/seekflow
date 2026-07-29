from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from seekflow.cli import app, run_repl
from seekflow.models import KBEntry


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


@pytest.mark.asyncio
async def test_workflow_continue_without_brief_reports_error(mocker, app_config, tmp_path) -> None:
    app_config.llm.api_key = "test-key"
    captured: dict[str, list] = {}

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
            captured["messages"] = messages
            self.command_handler = command_handler

        def refresh(self) -> None:
            return None

        def schedule_refresh(self) -> None:
            return None

        async def run(self) -> None:
            await self.command_handler("/workflow continue search_to_article")

    mocker.patch("seekflow.cli.SeekFlowTUI", FakeTUI)

    await run_repl(app_config)

    assert any("No recent brief is available" in message.body for message in captured["messages"])


@pytest.mark.asyncio
async def test_workflow_run_search_to_article_updates_transcript_and_state(mocker, app_config, tmp_path) -> None:
    app_config.llm.api_key = "test-key"
    captured: dict[str, list] = {}
    brief_entry = KBEntry(
        title="python gil",
        date=datetime.now(UTC),
        query="python gil",
        answer="brief body",
        tags=["python"],
        category="programming",
        provider="duckduckgo",
        model=app_config.llm.model,
        summary="brief summary",
        sources=[],
        file_path=tmp_path / "brief.md",
    )

    class FakePipeline:
        async def run(self, text, config, on_chunk, on_sources):
            on_chunk("brief body")
            return brief_entry

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
            captured["messages"] = messages
            self.command_handler = command_handler

        def refresh(self) -> None:
            return None

        def schedule_refresh(self) -> None:
            return None

        async def run(self) -> None:
            await self.command_handler("/workflow run search_to_article python gil")

    async def fake_save_entry(entry, kb_dir, obsidian_mode=False):
        entry.file_path = tmp_path / "article.md"
        return entry.file_path

    mocker.patch("seekflow.cli.SearchPipeline", return_value=FakePipeline())
    mocker.patch("seekflow.cli.SeekFlowTUI", FakeTUI)
    mocker.patch(
        "seekflow.workflows.adapters._run_command",
        side_effect=[("outline text", "", 0), ("article text", "", 0)],
    )
    mocker.patch("seekflow.workflows.content.save_entry", side_effect=fake_save_entry)

    await run_repl(app_config)

    assert any(message.title == "Outline" and "outline text" in message.body for message in captured["messages"])
    assert any(message.title == "Article" and "article text" in message.body for message in captured["messages"])
    assert any(message.title == "Saved" and "article.md" in message.body for message in captured["messages"])
