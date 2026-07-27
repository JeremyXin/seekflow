import pytest
from types import SimpleNamespace
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.document import Document
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Screen, WritePosition
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

from seekflow.output.formatter import SessionMessage
from seekflow.repl.session import SeekFlowTUI, build_input_hint_text, dispatch_input



def _render_transcript_rows(tui: SeekFlowTUI, *, width: int, height: int) -> list[str]:
    del width
    content_lines = tui.transcript_control.text.splitlines() or [""]
    top_line = min(tui.transcript_area.vertical_scroll, max(0, len(content_lines) - height))
    visible_lines = content_lines[top_line : top_line + height]
    return visible_lines + [""] * max(0, height - len(visible_lines))


def _render_transcript_window(tui: SeekFlowTUI, *, width: int, height: int) -> None:
    screen = Screen()
    tui.transcript_area.write_to_screen(
        screen,
        MouseHandlers(),
        WritePosition(xpos=0, ypos=0, width=width, height=height),
        parent_style="",
        erase_bg=False,
        z_index=None,
    )
    return screen


def _render_transcript_window_lines(tui: SeekFlowTUI, *, width: int, height: int) -> list[str]:
    screen = _render_transcript_window(tui, width=width, height=height)
    return [
        "".join(screen.data_buffer[y][x].char for x in range(width)).rstrip()
        for y in range(height)
    ]


def _make_long_reply(chunk_count: int = 120) -> str:
    return " ".join(f"chunk{index:02d}" for index in range(chunk_count))


@pytest.mark.asyncio
async def test_dispatches_slash_command() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_chat(text: str) -> None:
        calls.append(("chat", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("/help", fake_command, fake_chat, fake_search, lambda: "search")
    assert calls == [("command", "/help")]


@pytest.mark.asyncio
async def test_dispatches_search_query_in_search_mode() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_chat(text: str) -> None:
        calls.append(("chat", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("python gil", fake_command, fake_chat, fake_search, lambda: "search")
    assert calls == [("search", "python gil")]


@pytest.mark.asyncio
async def test_dispatches_chat_query_in_chat_mode() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_chat(text: str) -> None:
        calls.append(("chat", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("explain descriptors", fake_command, fake_chat, fake_search, lambda: "chat")
    assert calls == [("chat", "explain descriptors")]


def test_build_input_hint_text_contains_repl_guidance() -> None:
    prompt = build_input_hint_text("search")
    assert "Shift-Tab toggle mode" in prompt
    assert "PgUp/PgDn scroll transcript" in prompt
    assert "/mode" in prompt
    assert "search" in prompt


def test_build_repl_view_returns_text_sections(app_config) -> None:
    from seekflow.repl.session import build_repl_view

    sections = build_repl_view(
        app_config,
        [SessionMessage(role="assistant", title="SeekFlow", body="hello")],
        "draft input",
        "chat",
    )

    assert "SeekFlow" in sections["header"]
    assert "hello" in sections["transcript"]
    assert sections["input"] == "draft input"


def test_refresh_without_header_skips_header_build_work(app_config, tmp_path, monkeypatch) -> None:
    from seekflow.repl import session as repl_session

    header_calls: list[tuple[object, int | None]] = []

    def fake_build_header_text(config, width=None):
        header_calls.append((config, width))
        return "HEADER"

    monkeypatch.setattr(repl_session, "build_header_text", fake_build_header_text)

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="hello")],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    assert len(header_calls) == 1

    header_calls.clear()
    tui.refresh(refresh_header=False)

    assert header_calls == []


def test_build_repl_view_returns_separate_header_and_transcript(app_config) -> None:
    from seekflow.repl.session import build_repl_view

    view = build_repl_view(
        app_config,
        [SessionMessage(role="assistant", title="SeekFlow", body="hello")],
        "draft input",
        "search",
    )

    assert "SeekFlow" in view["header"]
    assert "hello" in view["transcript"]
    assert "hello" not in view["header"]
    assert view["input"] == "draft input"


def test_transcript_area_is_not_a_textarea_scrollbar_surface(app_config, tmp_path) -> None:
    from prompt_toolkit.widgets import TextArea

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="hello")],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    assert not isinstance(getattr(tui, "transcript_area", None), TextArea)


def test_header_area_is_rendered_separately_from_transcript(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    assert hasattr(tui, "header_area")
    assert hasattr(tui, "transcript_area")
    assert tui.transcript_area.dont_extend_height()


def test_transcript_area_prewraps_without_visible_scrollbar(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="long line " * 40)],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    assert tui.transcript_area.wrap_lines() is False
    assert tui.transcript_control.text.count("\n") > 2


def test_append_stream_chunk_builds_assistant_message() -> None:
    from seekflow.repl.session import append_stream_chunk

    messages: list[SessionMessage] = []

    append_stream_chunk(messages, "Hello")
    append_stream_chunk(messages, " world")

    assert messages[-1].role == "assistant"
    assert messages[-1].body == "Hello world"


@pytest.mark.asyncio
async def test_submit_exception_becomes_error_message_and_restores_input(app_config, tmp_path) -> None:
    async def failing_command(text: str) -> None:
        raise RuntimeError(f"boom: {text}")

    async def unused_search(text: str) -> None:
        raise AssertionError("search handler should not be called")

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        failing_command,
        unused_search,
        unused_search,
        lambda: "search",
        lambda mode: None,
    )
    tui.input_area.buffer.text = "/help"

    await tui._submit_current_input()

    assert tui.input_area.text == "/help"
    assert tui.messages[-1].role == "error"
    assert "boom: /help" in tui.messages[-1].body


def test_shift_tab_toggles_mode_and_updates_prompt(app_config, tmp_path) -> None:
    mode = "search"

    def get_mode() -> str:
        return mode

    def set_mode(new_mode: str) -> None:
        nonlocal mode
        mode = new_mode

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        get_mode,
        set_mode,
    )

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("s-tab",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert mode == "chat"
    prompt_factory = tui.input_area.control.input_processors[2].text
    assert "[chat]" in prompt_factory()[0][1]


def test_mode_prompt_is_dynamic(app_config, tmp_path) -> None:
    mode = "search"

    def get_mode() -> str:
        return mode

    def set_mode(new_mode: str) -> None:
        nonlocal mode
        mode = new_mode

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        get_mode,
        set_mode,
    )

    prompt_factory = tui.input_area.control.input_processors[2].text
    assert "[search]" in prompt_factory()[0][1]

    set_mode("chat")

    assert "[chat]" in prompt_factory()[0][1]


def test_mode_command_completion_offers_subcommands(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    completions = [
        completion.text
        for completion in tui.input_area.completer.get_completions(Document("/mode ", len("/mode ")), None)
    ]

    assert completions == ["status", "chat", "search"]


def test_pageup_scrolls_transcript_without_changing_input(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.input_area.buffer.text = "draft input"
    tui.transcript_area.vertical_scroll = 20

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("pageup",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert tui.transcript_area.vertical_scroll < 20
    assert tui.input_area.text == "draft input"
    assert tui._follow_output is False


def test_transcript_scroll_helpers_get_and_set_scroll(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(50)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    tui._set_transcript_scroll(20)

    assert tui._get_transcript_scroll() == 20


def test_transcript_scroll_survives_real_prompt_toolkit_render_path(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(80)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.refresh(refresh_header=False)
    tui._set_transcript_scroll(20)

    _render_transcript_window(tui, width=24, height=5)

    assert tui._get_transcript_scroll() == 20


def test_pageup_uses_transcript_scroll_controller(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    calls: list[str] = []

    def fake_page_up() -> None:
        calls.append("page-up")

    tui._page_up_transcript = fake_page_up

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("pageup",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert calls == ["page-up"]


def test_ctrl_up_scrolls_transcript_in_small_steps(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.transcript_area.vertical_scroll = 20

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("c-up",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert tui.transcript_area.vertical_scroll == 17
    assert tui._follow_output is False


def test_mouse_support_is_enabled_for_trackpad_scroll(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )

    assert tui.application.mouse_support()


def test_mouse_scroll_on_input_area_uses_transcript_scroll_controller(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    calls: list[int] = []

    def fake_scroll(delta: int) -> None:
        calls.append(delta)

    tui._scroll_transcript = fake_scroll

    tui.input_area.control.mouse_handler(
        MouseEvent(
            position=Point(x=0, y=0),
            event_type=MouseEventType.SCROLL_UP,
            button=MouseButton.NONE,
            modifiers=frozenset(),
        )
    )

    assert calls == [-3]


@pytest.mark.parametrize(
    ("event_type", "starting_scroll", "expected_scroll"),
    [
        (MouseEventType.SCROLL_UP, 20, 17),
        (MouseEventType.SCROLL_DOWN, 20, 23),
    ],
)
def test_mouse_scroll_on_input_area_scrolls_transcript(
    app_config,
    tmp_path,
    event_type,
    starting_scroll,
    expected_scroll,
) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.input_area.buffer.text = "draft input"
    tui.transcript_area.vertical_scroll = starting_scroll
    tui.application.layout.focus(tui.input_area)

    tui.input_area.control.mouse_handler(
        MouseEvent(
            position=Point(x=0, y=0),
            event_type=event_type,
            button=MouseButton.NONE,
            modifiers=frozenset(),
        )
    )

    assert tui.transcript_area.vertical_scroll == expected_scroll
    assert tui.input_area.text == "draft input"
    assert tui.application.layout.current_control == tui.input_area.control
    assert tui._follow_output is False


def test_refresh_preserves_scroll_position_when_follow_output_disabled(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.transcript_area.vertical_scroll = 12
    tui._follow_output = False
    tui.messages.append(SessionMessage(role="assistant", title="SeekFlow", body="new reply"))

    tui.refresh(refresh_header=False)

    assert tui.transcript_area.vertical_scroll == 12


def test_scroll_to_bottom_reenables_follow_output(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(200)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui._follow_output = False

    tui._scroll_to_bottom()

    assert tui._follow_output is True


def test_end_key_refreshes_pending_streamed_tail_before_jumping_to_bottom(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body="\n".join(f"line {i}" for i in range(80)))],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.application.output.get_size = lambda: Size(rows=24, columns=24)
    tui.refresh(refresh_header=False)
    tui._follow_output = False
    tui.transcript_area.vertical_scroll = 5
    tui.messages[-1].body += "\nLATEST STREAMED TAIL"

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("end",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    rows = _render_transcript_window_lines(tui, width=24, height=19)

    assert tui._follow_output is True
    assert "LATEST STREAMED TAIL" in tui.transcript_control.text
    assert any("LATEST STREAMED TAIL" in row for row in rows)


def test_refresh_prewraps_transcript_into_real_lines_for_scrolling(app_config, tmp_path) -> None:
    long_reply = _make_long_reply()
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body=long_reply)],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.application.output.get_size = lambda: Size(rows=24, columns=24)

    tui.refresh(refresh_header=False)

    assert tui.transcript_area.wrap_lines() is False
    assert tui.transcript_control.text.count("\n") > 2
    assert "chunk59" in tui.transcript_control.text




def _make_search_mode_messages() -> list[SessionMessage]:
    return [
        SessionMessage(role="user", title="You", body="compare asyncio vs threading for network clients"),
        SessionMessage(
            role="tool",
            title="Web Search",
            body="Provider: duckduckgo\nQuery: compare asyncio vs threading for network clients",
        ),
        SessionMessage(
            role="assistant",
            title="SeekFlow",
            body=(
                "Asyncio usually wins for many concurrent I/O-bound tasks because one event loop can "
                "multiplex waits efficiently while threads add scheduler and memory overhead. "
                "Threads remain useful for blocking integrations and small migration steps. " * 4
            ).strip(),
        ),
        SessionMessage(
            role="sources",
            title="Sources",
            body="[1] Python docs\nhttps://docs.python.org/3/library/asyncio.html\n\n[2] Real Python\nhttps://realpython.com/async-io-python/",
        ),
        SessionMessage(role="saved", title="Saved", body="Saved to /tmp/seekflow-asyncio-vs-threading.md"),
    ]


def test_refresh_tracks_real_line_count_for_mixed_search_mode_messages(app_config, tmp_path) -> None:
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        _make_search_mode_messages(),
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.application.output.get_size = lambda: Size(rows=24, columns=40)

    tui.refresh(refresh_header=False)

    transcript_lines = tui.transcript_control.text.splitlines()
    assert len(transcript_lines) > 20
    assert tui._get_transcript_rendered_row_count(40) == len(transcript_lines)
    assert "Sources" in tui.transcript_control.text
    assert "Saved to" in tui.transcript_control.text
    assert "seekflow-asyncio-vs-threading.md" in tui.transcript_control.text


def test_mouse_scroll_on_input_area_scrolls_search_transcript_without_touching_input_or_mode(app_config, tmp_path) -> None:
    mode = "search"

    def get_mode() -> str:
        return mode

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        _make_search_mode_messages(),
        lambda text: None,
        lambda text: None,
        lambda text: None,
        get_mode,
        lambda new_mode: None,
    )
    tui.application.output.get_size = lambda: Size(rows=24, columns=40)
    tui.refresh(refresh_header=False)
    tui.input_area.buffer.text = "draft input while reading results"
    tui._set_transcript_scroll(20)
    tui.application.layout.focus(tui.input_area)

    tui.input_area.control.mouse_handler(
        MouseEvent(
            position=Point(x=0, y=0),
            event_type=MouseEventType.SCROLL_UP,
            button=MouseButton.NONE,
            modifiers=frozenset(),
        )
    )

    assert tui._get_transcript_scroll() == 17
    assert tui.input_area.text == "draft input while reading results"
    assert tui.application.layout.current_control == tui.input_area.control
    assert tui.get_mode() == "search"
    assert tui._follow_output is False


def test_pageup_scrolls_search_transcript_without_mode_specific_branching(app_config, tmp_path) -> None:
    mode = "search"

    def get_mode() -> str:
        return mode

    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        _make_search_mode_messages(),
        lambda text: None,
        lambda text: None,
        lambda text: None,
        get_mode,
        lambda new_mode: None,
    )
    tui.application.output.get_size = lambda: Size(rows=24, columns=40)
    tui.refresh(refresh_header=False)
    tui.input_area.buffer.text = "draft input while reading results"
    tui._set_transcript_scroll(20)
    calls: list[int] = []
    original_scroll = tui._scroll_transcript

    def recording_scroll(delta: int) -> None:
        calls.append(delta)
        original_scroll(delta)

    tui._scroll_transcript = recording_scroll

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("pageup",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    assert calls == [-10]
    assert tui._get_transcript_scroll() == 10
    assert tui.input_area.text == "draft input while reading results"
    assert tui.application.layout.current_control == tui.input_area.control
    assert tui.get_mode() == "search"
    assert tui._follow_output is False

def test_end_key_reaches_true_visible_bottom_for_wrapped_transcript_output(app_config, tmp_path) -> None:
    long_reply = _make_long_reply()
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body=long_reply)],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.application.output.get_size = lambda: Size(rows=24, columns=24)
    tui._follow_output = False
    tui.transcript_area.vertical_scroll = 0
    tui.refresh(refresh_header=False)

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("end",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)

    rows = _render_transcript_window_lines(tui, width=24, height=19)

    assert tui._follow_output is True
    assert any("chunk119" in row for row in rows)
    assert not any("chunk00" in row for row in rows)


def test_end_then_first_pageup_moves_up_from_real_bottom_without_overscroll(app_config, tmp_path) -> None:
    long_reply = _make_long_reply(chunk_count=220)
    tui = SeekFlowTUI(
        app_config,
        tmp_path / "history",
        [SessionMessage(role="assistant", title="SeekFlow", body=long_reply)],
        lambda text: None,
        lambda text: None,
        lambda text: None,
        lambda: "search",
        lambda mode: None,
    )
    tui.application.output.get_size = lambda: Size(rows=24, columns=24)
    tui.refresh(refresh_header=False)
    _render_transcript_window(tui, width=24, height=19)

    tui._scroll_to_bottom()
    _render_transcript_window(tui, width=24, height=19)
    expected_bottom_scroll = max(0, len(tui.transcript_control.text.splitlines()) - 19)

    assert tui._get_transcript_scroll() == expected_bottom_scroll

    binding = next(
        binding
        for binding in tui.application.key_bindings.bindings
        if binding.keys == ("pageup",)
    )
    event = SimpleNamespace(app=tui.application)

    binding.handler(event)
    _render_transcript_window(tui, width=24, height=19)

    assert tui._get_transcript_scroll() == max(0, expected_bottom_scroll - 10)
