from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.completion import NestedCompleter
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
    chat_handler: Callable[[str], Awaitable[None]],
    search_handler: Callable[[str], Awaitable[None]],
    get_mode: Callable[[], str],
) -> None:
    stripped = text.strip()
    if not stripped:
        return
    if stripped.startswith("/"):
        await command_handler(stripped)
        return
    if get_mode() == "chat":
        await chat_handler(stripped)
        return
    await search_handler(stripped)


def build_input_hint_text(mode: str) -> str:
    return (
        f"  mode={mode} · Shift-Tab toggle mode · "
        f"PgUp/PgDn scroll transcript · End jump bottom · /mode status · /help"
    )


def build_command_completer() -> NestedCompleter:
    return NestedCompleter.from_nested_dict(
        {
            "/help": None,
            "/config": {"show": None},
            "/provider": {"list": None, "status": None, "switch": None},
            "/kb": {"list": None, "search": None, "show": None, "delete": None},
            "/mode": {"status": None, "chat": None, "search": None},
            "/save": None,
            "/exit": None,
            "/quit": None,
        }
    )


def build_repl_view(config, messages: list[SessionMessage], current_input: str, mode: str) -> dict[str, str]:
    return {
        "body": build_repl_body_text(config, messages),
        "input": current_input,
        "hint": build_input_hint_text(mode),
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
        chat_handler: Callable[[str], Awaitable[None]],
        search_handler: Callable[[str], Awaitable[None]],
        get_mode: Callable[[], str],
        set_mode: Callable[[str], None],
    ) -> None:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.messages = messages
        self.command_handler = command_handler
        self.chat_handler = chat_handler
        self.search_handler = search_handler
        self.get_mode = get_mode
        self.set_mode = set_mode
        self._refresh_handle: asyncio.TimerHandle | None = None
        self._pending_header_refresh = False
        self._submit_in_flight = False
        self._follow_output = True

        self.body_area = TextArea(
            text="",
            read_only=True,
            focusable=True,
            scrollbar=True,
            wrap_lines=True,
            dont_extend_height=True,
            style="class:transcript",
        )
        self.input_area = TextArea(
            text="",
            multiline=False,
            history=FileHistory(str(history_path)),
            completer=build_command_completer(),
            height=1,
            dont_extend_height=True,
            prompt=self._prompt_fragments,
            style="class:input",
        )
        self.input_hint_area = TextArea(
            text=build_input_hint_text(self.get_mode()),
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

        @bindings.add("s-tab")
        def _toggle_mode(event) -> None:
            self._toggle_mode()
            event.app.invalidate()

        @bindings.add("pageup")
        def _page_up(event) -> None:
            self._scroll_body(-10)
            event.app.invalidate()

        @bindings.add("c-up")
        def _scroll_up(event) -> None:
            self._scroll_body(-3)
            event.app.invalidate()

        @bindings.add("pagedown")
        def _page_down(event) -> None:
            self._scroll_body(10)
            event.app.invalidate()

        @bindings.add("c-down")
        def _scroll_down(event) -> None:
            self._scroll_body(3)
            event.app.invalidate()

        @bindings.add("end")
        def _jump_bottom(event) -> None:
            self._scroll_to_bottom()
            event.app.invalidate()

        return bindings

    def _build_prompt_text(self) -> str:
        return f"[{self.get_mode()}] ❯ "

    def _prompt_fragments(self) -> list[tuple[str, str]]:
        return [("class:prompt", self._build_prompt_text())]

    def _toggle_mode(self) -> None:
        new_mode = "chat" if self.get_mode() == "search" else "search"
        self.set_mode(new_mode)
        self.messages.append(SessionMessage(role="system", title="System", body=f"Mode switched to {new_mode}"))
        self.refresh(refresh_header=False)

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

    def _scroll_body(self, delta: int) -> None:
        self.body_area.window.vertical_scroll = max(0, self.body_area.window.vertical_scroll + delta)
        self._follow_output = False

    def _scroll_to_bottom(self) -> None:
        self._follow_output = True
        self.refresh(refresh_header=False)

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
            await dispatch_input(
                text,
                self.command_handler,
                self.chat_handler,
                self.search_handler,
                self.get_mode,
            )
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
        view = build_repl_view(self.config, self.messages, self.input_area.text, self.get_mode())
        view["body"] = build_repl_body_text(self.config, self.messages, width=width)
        current_cursor_position = min(self.body_area.buffer.cursor_position, len(view["body"]))
        current_scroll = self.body_area.window.vertical_scroll
        if self._follow_output:
            cursor_position = len(view["body"])
        else:
            cursor_position = current_cursor_position
        self.body_area.buffer.set_document(
            Document(view["body"], cursor_position=cursor_position),
            bypass_readonly=True,
        )
        if self._follow_output:
            self.body_area.window.vertical_scroll = max(0, len(view["body"].splitlines()) - 1)
        else:
            self.body_area.window.vertical_scroll = current_scroll
        self.input_hint_area.buffer.set_document(
            Document(view["hint"], cursor_position=len(view["hint"])),
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
