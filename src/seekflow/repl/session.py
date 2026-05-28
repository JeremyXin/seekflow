from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from seekflow.output.formatter import (
    SessionMessage,
    build_error_message,
    build_repl_body_text,
)


async def dispatch_input(
    text: str,
    command_handler: Callable[[str], Awaitable[None]],
    search_handler: Callable[[str], Awaitable[None]],
) -> None:
    stripped = text.strip()
    if not stripped:
        return
    if stripped.startswith("/"):
        await command_handler(stripped)
        return
    await search_handler(stripped)


def build_input_hint_text() -> str:
    return "  ? for shortcuts"


def build_repl_view(config, messages: list[SessionMessage], current_input: str) -> dict[str, str]:
    return {
        "body": build_repl_body_text(config, messages),
        "input": current_input,
    }


def append_stream_chunk(messages: list[SessionMessage], chunk: str) -> SessionMessage:
    if not messages or messages[-1].role != "assistant":
        messages.append(SessionMessage(role="assistant", title="SeekFlow", body=""))
    messages[-1].body += chunk
    return messages[-1]


class SeekFlowTUI:
    def __init__(
        self,
        config,
        history_path: Path,
        messages: list[SessionMessage],
        command_handler: Callable[[str], Awaitable[None]],
        search_handler: Callable[[str], Awaitable[None]],
    ) -> None:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.messages = messages
        self.command_handler = command_handler
        self.search_handler = search_handler
        self._refresh_handle: asyncio.TimerHandle | None = None
        self._pending_header_refresh = False
        self._submit_in_flight = False

        self.body_area = TextArea(
            text="",
            read_only=True,
            focusable=False,
            scrollbar=False,
            wrap_lines=True,
            dont_extend_height=True,
            style="class:transcript",
        )
        self.input_area = TextArea(
            text="",
            multiline=False,
            history=FileHistory(str(history_path)),
            height=1,
            dont_extend_height=True,
            prompt=[("class:prompt", "❯ ")],
            style="class:input",
        )
        self.input_hint_area = TextArea(
            text=build_input_hint_text(),
            read_only=True,
            focusable=False,
            height=1,
            wrap_lines=False,
            style="class:hint",
        )

        root = HSplit(
            [
                self.body_area,
                Window(height=1, char="─", style="class:separator"),
                self.input_area,
                Window(height=1, char="─", style="class:separator"),
                self.input_hint_area,
                Window(),
            ]
        )
        self.application = Application(
            layout=Layout(root, focused_element=self.input_area),
            key_bindings=self._build_key_bindings(),
            style=self._build_style(),
            full_screen=True,
        )
        self.refresh(refresh_header=True)

    def _build_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("c-c")
        def _exit(event) -> None:
            event.app.exit()

        @bindings.add("enter")
        def _submit(event) -> None:
            event.app.create_background_task(self._submit_current_input())

        return bindings

    def _build_style(self) -> Style:
        return Style.from_dict(
            {
                "header": "bg:#111418 #d8dde6",
                "transcript": "bg:#111418 #cfd6df",
                "hint": "bg:#111418 #7f8a98",
                "prompt": "bg:#111418 bold #f5f7fb",
                "input": "bg:#111418 #eef2f7",
                "separator": "bg:#111418 #2a313a",
            }
        )

    async def _submit_current_input(self) -> None:
        if self._submit_in_flight:
            return
        text = self.input_area.text
        message_count_before_submit = len(self.messages)
        self.input_area.buffer.set_document(Document("", cursor_position=0))
        self.application.invalidate()
        if text.strip() in {"/exit", "/quit"}:
            self.application.exit()
            return
        self._submit_in_flight = True
        try:
            await dispatch_input(text, self.command_handler, self.search_handler)
        except Exception as exc:
            if len(self.messages) == message_count_before_submit:
                self.input_area.buffer.set_document(
                    Document(text, cursor_position=len(text)),
                )
            self.messages.append(build_error_message(str(exc)))
            self.refresh(refresh_header=False)
        finally:
            self._submit_in_flight = False
            self.application.layout.focus(self.input_area)
            self.application.invalidate()

    def refresh(self, refresh_header: bool = True) -> None:
        width = max(76, self.application.output.get_size().columns - 4)
        view = {
            "body": build_repl_body_text(self.config, self.messages, width=width),
            "input": self.input_area.text,
        }
        self.body_area.buffer.set_document(
            Document(view["body"], cursor_position=len(view["body"])),
            bypass_readonly=True,
        )
        self.application.invalidate()

    def schedule_refresh(self, delay: float = 0.05, refresh_header: bool = False) -> None:
        loop = asyncio.get_running_loop()
        self._pending_header_refresh = self._pending_header_refresh or refresh_header
        if self._refresh_handle is not None and not self._refresh_handle.cancelled():
            return
        self._refresh_handle = loop.call_later(delay, self._flush_scheduled_refresh)

    def _flush_scheduled_refresh(self) -> None:
        self._refresh_handle = None
        refresh_header = self._pending_header_refresh
        self._pending_header_refresh = False
        self.refresh(refresh_header=refresh_header)

    async def run(self) -> None:
        await self.application.run_async()
