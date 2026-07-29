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
)
from seekflow.pipeline import SearchPipeline
from seekflow.repl.commands import handle_command
from seekflow.repl.workflows import WorkflowSessionState
from seekflow.repl.session import SeekFlowTUI, append_stream_chunk
from seekflow.workflows.content import build_brief_to_article_spec, build_brief_to_article_steps
from seekflow.workflows.models import Artifact
from seekflow.workflows.runner import WorkflowRunner

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
    messages: list[SessionMessage] = []
    conversation_history: list[ConversationTurn] = []
    latest_chat: tuple[str, str] | None = None
    current_mode = "search"
    workflow_state = WorkflowSessionState()
    tui: SeekFlowTUI | None = None

    def redraw() -> None:
        if tui is not None:
            tui.refresh()

    def schedule_redraw() -> None:
        if tui is not None:
            tui.schedule_refresh()

    async def emit(text: str) -> None:
        messages.append(SessionMessage(role="system", title="System", body=text))
        redraw()

    def get_mode() -> str:
        return current_mode

    def set_mode(mode: str) -> None:
        nonlocal current_mode
        current_mode = mode

    async def run_article_workflow_from_brief(brief_entry) -> None:
        messages.append(SessionMessage(role="tool", title="Workflow", body="Workflow: search_to_article"))
        redraw()

        context = {
            "config": config,
            "brief_entry": brief_entry,
        }
        runner = WorkflowRunner(build_brief_to_article_spec(), build_brief_to_article_steps())
        final_artifact = await runner.run(
            initial_artifact=Artifact(name="kb_entry", payload=brief_entry),
            context=context,
        )
        workflow_state.latest_workflow_name = "search_to_article"
        workflow_state.latest_outline_artifact = context.get("outline_artifact")
        workflow_state.latest_article_artifact = context.get("article_artifact")

        outline_artifact = context.get("outline_artifact")
        if outline_artifact is not None:
            messages.append(SessionMessage(role="assistant", title="Outline", body=str(outline_artifact.payload)))

        article_artifact = context.get("article_artifact")
        if article_artifact is not None:
            messages.append(SessionMessage(role="assistant", title="Article", body=str(article_artifact.payload)))

        entry = final_artifact.payload
        if entry.file_path:
            messages.append(build_saved_message(entry.file_path))
        redraw()

    async def workflow_handler(action: str, name: str, value: str | None = None) -> None:
        if action == "status":
            await emit(
                "workflow="
                f"{workflow_state.latest_workflow_name or 'none'} "
                f"recent_brief={'yes' if workflow_state.latest_brief_entry is not None else 'no'} "
                f"recent_article={'yes' if workflow_state.latest_article_artifact is not None else 'no'}"
            )
            return

        if name != "search_to_article":
            await emit(f"Unknown workflow: {name}")
            return

        if not config.llm.api_key:
            messages.append(
                build_error_message(
                    "LLM API key is not configured.",
                    "Set SEEKFLOW_LLM_API_KEY or edit ~/.seekflow/config.toml before running workflows.",
                )
            )
            redraw()
            return

        if action == "run":
            query = value or ""
            assistant_message: SessionMessage | None = None

            def on_chunk(chunk: str) -> None:
                nonlocal assistant_message
                assistant_message = append_stream_chunk(messages, chunk)
                schedule_redraw()

            try:
                brief_entry = await pipeline.run(query, config, on_chunk=on_chunk, on_sources=None)
            except Exception as exc:
                messages.append(build_error_message(str(exc)))
                redraw()
                return

            workflow_state.latest_brief_entry = brief_entry
            if brief_entry.file_path:
                messages.append(build_saved_message(brief_entry.file_path))
            await run_article_workflow_from_brief(brief_entry)
            return

        if action == "continue":
            if workflow_state.latest_brief_entry is None:
                await emit(
                    "No recent brief is available. Run a search first or use /workflow run search_to_article <query>."
                )
                return
            try:
                await run_article_workflow_from_brief(workflow_state.latest_brief_entry)
            except Exception as exc:
                messages.append(build_error_message(str(exc)))
                redraw()
            return

    async def command_handler(text: str) -> None:
        nonlocal latest_chat
        messages.append(SessionMessage(role="user", title="You", body=text))
        redraw()
        await handle_command(
            text,
            config,
            emit,
            latest_chat=latest_chat,
            workflow_handler=workflow_handler,
            get_mode=get_mode,
            set_mode=set_mode,
        )

    async def chat_handler(text: str) -> None:
        nonlocal latest_chat
        messages.append(SessionMessage(role="user", title="You", body=text))
        redraw()

        if not config.llm.api_key:
            messages.append(
                build_error_message(
                    "LLM API key is not configured.",
                    "Set SEEKFLOW_LLM_API_KEY or edit ~/.seekflow/config.toml before chatting.",
                )
            )
            redraw()
            return

        assistant_message: SessionMessage | None = None

        def on_chunk(chunk: str) -> None:
            nonlocal assistant_message
            assistant_message = append_stream_chunk(messages, chunk)
            schedule_redraw()

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

        assistant_message: SessionMessage | None = None

        def on_chunk(chunk: str) -> None:
            nonlocal assistant_message
            assistant_message = append_stream_chunk(messages, chunk)
            schedule_redraw()

        messages.append(
            SessionMessage(
                role="tool",
                title="Web Search",
                body=f"Provider: {config.app.default_provider}",
            )
        )
        redraw()

        try:
            entry = await pipeline.run(text, config, on_chunk=on_chunk, on_sources=None)
        except Exception as exc:
            messages.append(build_error_message(str(exc)))
            redraw()
            return

        workflow_state.latest_brief_entry = entry
        workflow_state.latest_workflow_name = "search_to_brief"
        if assistant_message is None and entry.answer:
            messages.append(SessionMessage(role="assistant", title="SeekFlow", body=entry.answer))
        messages.append(build_sources_message(entry.sources))
        if entry.file_path:
            messages.append(build_saved_message(entry.file_path))
        redraw()

    tui = SeekFlowTUI(
        config,
        config.knowledge_base.kb_dir.parent / "history",
        messages,
        command_handler,
        chat_handler,
        search_handler,
        get_mode,
        set_mode,
    )
    redraw()
    await tui.run()
