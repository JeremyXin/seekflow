from dataclasses import dataclass
from pathlib import Path

from rich import box
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from seekflow import __version__
from seekflow.models import SearchResult


console = Console()


@dataclass(slots=True)
class SessionMessage:
    role: str
    title: str
    body: str


def build_ascii_logo() -> str:
    return (
        " ____             _     _____ _               \n"
        "/ ___|  ___  ___| | __|  ___| | _____      __\n"
        "\\___ \\ / _ \\/ _ \\ |/ /| |_  | |/ _ \\ \\ /\\ / /\n"
        " ___) |  __/  __/   < |  _| | | (_) \\ V  V / \n"
        "|____/ \\___|\\___|_|\\_\\|_|   |_|\\___/ \\_/\\_/  "
    )


def _collect_recent_activity(kb_dir: Path) -> str:
    entries = sorted(kb_dir.glob("**/*.md"))
    if not entries:
        return "No recent activity"
    latest = entries[-1]
    return f"{len(entries)} saved entries · latest: {latest.stem}"


def _render_left_header(config) -> RenderableType:
    return Group(
        Text("Welcome", style="bold cyan"),
        Text(build_ascii_logo(), style="bold white"),
        Text(f"v{__version__}", style="bright_black"),
        Text(f"provider: {config.app.default_provider}", style="white"),
        Text(f"model: {config.llm.model}", style="white"),
    )


def _render_right_header(config) -> RenderableType:
    return Group(
        Text("Session", style="bold cyan"),
        Text("Tips: use /provider list to inspect engines and /kb list to browse saved notes.", style="white"),
        Text(f"Recent activity: {_collect_recent_activity(config.knowledge_base.kb_dir)}", style="white"),
        Text(f"Knowledge base: {config.knowledge_base.kb_dir}", style="white"),
    )


def _render_message(message: SessionMessage) -> Panel:
    style_map = {
        "user": ("You", "bright_blue"),
        "assistant": ("SeekFlow", "white"),
        "error": ("Error", "red"),
        "system": ("System", "bright_black"),
        "sources": ("Sources", "yellow"),
        "saved": ("Saved", "green"),
    }
    fallback_title, border_style = style_map.get(message.role, (message.title, "white"))
    title = message.title or fallback_title
    return Panel(
        Text(message.body or " ", style="white"),
        title=title,
        title_align="left",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def build_sources_message(results: list[SearchResult]) -> SessionMessage:
    if not results:
        return SessionMessage(role="sources", title="Sources", body="No sources")
    body = "\n".join(f"[{index}] {item.title}\n{item.url}" for index, item in enumerate(results, start=1))
    return SessionMessage(role="sources", title="Sources", body=body)


def build_saved_message(path: Path) -> SessionMessage:
    return SessionMessage(role="saved", title="Saved", body=f"Saved to {path}")


def build_error_message(message: str, suggestion: str | None = None) -> SessionMessage:
    body = message
    if suggestion:
        body = f"{body}\n{suggestion}"
    return SessionMessage(role="error", title="Error", body=body)


def build_app_shell(config, messages: list[SessionMessage]) -> RenderableType:
    header = Panel(
        Columns(
            [
                Panel(_render_left_header(config), border_style="cyan", box=box.ROUNDED),
                Panel(_render_right_header(config), border_style="cyan", box=box.ROUNDED),
            ],
            equal=True,
            expand=True,
        ),
        title=f"SeekFlow v{__version__}",
        title_align="left",
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(1, 1),
    )

    rendered_messages = messages[-10:] if messages else [SessionMessage(role="system", title="System", body='Try "compare asyncio vs threading in Python"')]
    message_group = Group(*[_render_message(message) for message in rendered_messages])
    body = Panel(
        message_group,
        title="Conversation",
        title_align="left",
        border_style="bright_black",
        box=box.ROUNDED,
        padding=(1, 1),
    )

    return Group(header, body)


def render_app_shell(config, messages: list[SessionMessage]) -> None:
    console.clear()
    console.print(build_app_shell(config, messages))


def show_info(message: str) -> None:
    console.print(message)


def show_error(message: str, suggestion: str | None = None) -> None:
    console.print(f"[red]{message}[/red]")
    if suggestion:
        console.print(f"[blue]{suggestion}[/blue]")


def show_sources(results: list[SearchResult]) -> None:
    for index, result in enumerate(results, start=1):
        console.print(f"[cyan][{index}][/cyan] {result.title} - {result.url}")


def show_saved_path(path) -> None:
    console.print(f"[green]Saved to {path}[/green]")
