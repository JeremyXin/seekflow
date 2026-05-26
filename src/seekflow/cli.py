import asyncio

import typer

from seekflow import __version__
from seekflow.config import ensure_config_exists, load_config
from seekflow.output.formatter import show_error, show_saved_path, show_sources
from seekflow.pipeline import SearchPipeline
from seekflow.repl.commands import handle_command
from seekflow.repl.session import build_session, repl_loop

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

    async def emit(text: str) -> None:
        typer.echo(text)

    async def command_handler(text: str) -> None:
        await handle_command(text, config, emit)

    async def search_handler(text: str) -> None:
        if not config.llm.api_key:
            show_error(
                "LLM API key is not configured.",
                "Set SEEKFLOW_LLM_API_KEY or edit ~/.seekflow/config.toml before searching.",
            )
            return

        chunks: list[str] = []

        def on_sources(results) -> None:
            show_sources(results)

        def on_chunk(chunk: str) -> None:
            chunks.append(chunk)
            typer.echo(chunk, nl=False)

        try:
            entry = await pipeline.run(text, config, on_chunk=on_chunk, on_sources=on_sources)
        except Exception as exc:
            typer.echo()
            show_error(str(exc))
            return

        if chunks:
            typer.echo()
        if entry.file_path:
            show_saved_path(entry.file_path)

    await repl_loop(config, command_handler, search_handler, session)
