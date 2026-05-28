import asyncio

import typer

from seekflow.chat.chat_engine import stream_chat_reply
from seekflow import __version__
from seekflow.config import ensure_config_exists, load_config
from seekflow.models import ConversationTurn
from seekflow.output.formatter import (
    SessionMessage,
    build_error_message,
    build_saved_message,
    build_sources_message,
    render_app_shell,
)
from seekflow.pipeline import SearchPipeline
from seekflow.repl.commands import handle_command
from seekflow.repl.session import build_session, repl_loop
from seekflow.routing.router import route_user_input

app = typer.Typer(help="Search, synthesize, and save answers to a local knowledge base.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"seekflow {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        ensure_config_exists()
        config = load_config()
        asyncio.run(run_repl(config))


@app.command()
def init() -> None:
    path = ensure_config_exists()
    typer.echo(f"Config created at {path}")


async def run_repl(config) -> None:
    pipeline = SearchPipeline()
    session = build_session(config.knowledge_base.kb_dir.parent / "history")
    messages: list[SessionMessage] = []
    conversation_history: list[ConversationTurn] = []
    latest_chat: tuple[str, str] | None = None

    def redraw() -> None:
        render_app_shell(config, messages)

    async def emit(text: str) -> None:
        messages.append(SessionMessage(role="system", title="System", body=text))
        redraw()

    async def command_handler(text: str) -> None:
        nonlocal latest_chat
        messages.append(SessionMessage(role="user", title="You", body=text))
        redraw()
        await handle_command(text, config, emit, latest_chat=latest_chat)

    async def search_handler(text: str) -> None:
        nonlocal latest_chat
        messages.append(SessionMessage(role="user", title="You", body=text))
        redraw()

        if not config.llm.api_key:
            messages.append(
                build_error_message(
                    "LLM API key is not configured.",
                    "Set SEEKFLOW_LLM_API_KEY or edit ~/.seekflow/config.toml before searching.",
                )
            )
            redraw()
            return

        try:
            decision = await route_user_input(text, config)
        except Exception as exc:
            messages.append(build_error_message(f"Routing failed: {exc}"))
            redraw()
            return

        assistant_message: SessionMessage | None = None
        messages.append(
            SessionMessage(
                role="system",
                title="Router",
                body=f"Mode: {decision.mode}\nReason: {decision.reason}",
            )
        )
        redraw()

        def on_chunk(chunk: str) -> None:
            nonlocal assistant_message
            if assistant_message is None:
                assistant_message = SessionMessage(role="assistant", title="SeekFlow", body="")
                messages.append(assistant_message)
            assistant_message.body += chunk
            redraw()

        if decision.mode == "chat":
            try:
                async for chunk in stream_chat_reply(text, conversation_history, config):
                    on_chunk(chunk)
            except Exception as exc:
                messages.append(build_error_message(str(exc)))
                redraw()
                return
            if assistant_message is None:
                messages.append(build_error_message("Chat mode returned an empty response."))
                redraw()
                return
            conversation_history.append(ConversationTurn(role="user", content=text))
            conversation_history.append(ConversationTurn(role="assistant", content=assistant_message.body))
            latest_chat = (text, assistant_message.body)
            redraw()
            return

        messages.append(
            SessionMessage(
                role="tool",
                title="Web Search",
                body=f"Reason: {decision.reason}\nProvider: {config.app.default_provider}",
            )
        )
        redraw()

        try:
            entry = await pipeline.run(text, config, on_chunk=on_chunk, on_sources=None)
        except Exception as exc:
            messages.append(build_error_message(str(exc)))
            redraw()
            return

        if assistant_message is None and entry.answer:
            messages.append(SessionMessage(role="assistant", title="SeekFlow", body=entry.answer))
        messages.append(build_sources_message(entry.sources))
        if entry.file_path:
            messages.append(build_saved_message(entry.file_path))
        latest_chat = None
        redraw()

    redraw()
    await repl_loop(config, command_handler, search_handler, session)
