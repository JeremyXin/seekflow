from rich.console import Console

from seekflow.models import SearchResult


console = Console()


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
