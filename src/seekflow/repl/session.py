from __future__ import annotations

import asyncio
import textwrap
from collections.abc import Awaitable, Callable
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.data_structures import Point
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, Window
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from seekflow.output.formatter import (
    SessionMessage,
    build_error_message,
    build_header_text,
    build_transcript_text,
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


def build_repl_view(
    config,
    messages: list[SessionMessage],
    current_input: str,
    mode: str,
    *,
    include_header: bool = True,
    header_width: int | None = None,
) -> dict[str, str]:
    return {
        "header": (build_header_text(config, width=header_width) if header_width is not None else build_header_text(config))
        if include_header
        else "",
        "transcript": build_transcript_text(messages),
        "input": current_input,
        "hint": build_input_hint_text(mode),
    }


def append_stream_chunk(messages: list[SessionMessage], chunk: str) -> SessionMessage:
    if not messages or messages[-1].role != "assistant":
        messages.append(SessionMessage(role="assistant", title="SeekFlow", body=""))
    messages[-1].body += chunk
    return messages[-1]


def _wrap_transcript_line(line: str, width: int) -> list[str]:
    width = max(1, width)
    if line == "":
        return [""]
    return textwrap.wrap(
        line,
        width=width,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=False,
    )


def prewrap_transcript_text(text: str, width: int) -> str:
    lines = text.split("\n") if text else [""]
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(_wrap_transcript_line(line, width))
    return "\n".join(wrapped_lines)


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
        self._last_output_columns: int | None = None
        self._last_output_rows: int | None = None

        self.header_control = FormattedTextControl(text="", focusable=False, show_cursor=False)
        self.header_area = Window(
            content=self.header_control,
            wrap_lines=True,
            dont_extend_height=True,
            style="class:header",
        )
        self.transcript_control = FormattedTextControl(
            text="",
            focusable=False,
            show_cursor=False,
            get_cursor_position=self._get_transcript_cursor_position,
        )
        self.transcript_area = Window(
            content=self.transcript_control,
            wrap_lines=False,
            dont_extend_height=True,
            style="class:transcript",
        )
        self._transcript_row_count = 0
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
                self.header_area,
                Window(height=1, char="─", style="class:separator"),
                self.transcript_area,
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
            mouse_support=True,
        )
        self._install_mouse_scroll_routing()
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
            self._page_up_transcript()
            event.app.invalidate()

        @bindings.add("c-up")
        def _scroll_up(event) -> None:
            self._scroll_transcript(-3)
            event.app.invalidate()

        @bindings.add("pagedown")
        def _page_down(event) -> None:
            self._page_down_transcript()
            event.app.invalidate()

        @bindings.add("c-down")
        def _scroll_down(event) -> None:
            self._scroll_transcript(3)
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

    def _install_mouse_scroll_routing(self) -> None:
        self.header_area.content.mouse_handler = self._build_scroll_mouse_handler(self.header_area.content.mouse_handler)
        self.transcript_area.content.mouse_handler = self._build_scroll_mouse_handler(self.transcript_area.content.mouse_handler)
        self.input_area.control.mouse_handler = self._build_scroll_mouse_handler(self.input_area.control.mouse_handler)
        self.input_hint_area.control.mouse_handler = self._build_scroll_mouse_handler(
            self.input_hint_area.control.mouse_handler
        )

    def _build_scroll_mouse_handler(self, delegate):
        def _mouse_handler(mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.SCROLL_UP:
                self._scroll_transcript(-3)
                self.application.invalidate()
                return None
            if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self._scroll_transcript(3)
                self.application.invalidate()
                return None
            return delegate(mouse_event)

        return _mouse_handler

    def _get_transcript_scroll(self) -> int:
        return self.transcript_area.vertical_scroll

    def _get_transcript_cursor_position(self) -> Point:
        return Point(
            x=0,
            y=min(self._get_transcript_scroll(), max(0, self._transcript_row_count - 1)),
        )

    def _get_transcript_viewport_rows(self) -> int:
        render_info = self.transcript_area.render_info
        if render_info is not None and render_info.displayed_lines:
            return max(1, len(render_info.displayed_lines))

        output_rows = self._last_output_rows or self.application.output.get_size().rows
        header_rows = max(1, len((self.header_control.text or "").splitlines()))
        fixed_rows = header_rows + 4  # header separator + input separator + input + hint separator + hint
        return max(1, output_rows - fixed_rows)

    def _get_max_transcript_scroll(self) -> int:
        return max(0, self._transcript_row_count - self._get_transcript_viewport_rows())

    def _set_transcript_scroll(self, value: int) -> None:
        self.transcript_area.vertical_scroll = max(0, min(value, self._get_max_transcript_scroll()))

    def _scroll_transcript(self, delta: int) -> None:
        self._set_transcript_scroll(self._get_transcript_scroll() + delta)
        self._follow_output = False

    def _page_up_transcript(self) -> None:
        self._scroll_transcript(-10)

    def _page_down_transcript(self) -> None:
        self._scroll_transcript(10)

    def _scroll_to_bottom(self) -> None:
        self._follow_output = True
        self.refresh(refresh_header=False)
        self._set_transcript_scroll_to_bottom()
        self.application.invalidate()

    def _set_transcript_scroll_to_bottom(self) -> None:
        self._set_transcript_scroll(self._get_max_transcript_scroll())

    def _get_transcript_rendered_row_count(self, width: int) -> int:
        del width
        return max(1, len(self.transcript_control.text.splitlines()))

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
        output_size = self.application.output.get_size()
        output_columns = output_size.columns
        output_rows = output_size.rows
        if self._last_output_columns is not None and output_columns != self._last_output_columns:
            refresh_header = True
        self._last_output_columns = output_columns
        self._last_output_rows = output_rows
        width = max(76, output_columns - 4)
        view = build_repl_view(
            self.config,
            self.messages,
            self.input_area.text,
            self.get_mode(),
            include_header=refresh_header,
            header_width=width,
        )
        current_scroll = self._get_transcript_scroll()

        if refresh_header:
            self.header_control.text = view["header"]

        transcript = prewrap_transcript_text(view["transcript"], output_columns)
        self.transcript_control.text = transcript
        self._transcript_row_count = self._get_transcript_rendered_row_count(output_columns)

        if self._follow_output:
            self._set_transcript_scroll_to_bottom()
        else:
            self._set_transcript_scroll(current_scroll)

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
