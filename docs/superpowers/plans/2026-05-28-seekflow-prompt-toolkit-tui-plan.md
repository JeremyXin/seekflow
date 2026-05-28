# SeekFlow Prompt Toolkit TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flashing full-screen redraw REPL with a persistent `prompt_toolkit` TUI that supports smooth streaming output.

**Architecture:** Build a dedicated prompt-toolkit application layer for SeekFlow REPL with a fixed header, scrollable transcript, and fixed input box. Preserve the existing message model and routing behavior while removing the interactive dependency on `Rich` full-screen redraws.

**Tech Stack:** Python 3.11, prompt-toolkit, Typer, pytest

---

### Task 1: Add prompt-toolkit transcript and header formatters

**Files:**
- Modify: `src/seekflow/output/formatter.py`
- Test: `tests/test_formatter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_header_text_contains_session_fields(app_config) -> None:
    from seekflow.output.formatter import build_header_text

    header = build_header_text(app_config)

    assert "SeekFlow" in header
    assert "Welcome back!" in header
    assert "provider: duckduckgo" in header
    assert "model: gpt-4o-mini" in header


def test_build_transcript_text_contains_roles_and_bodies() -> None:
    from seekflow.output.formatter import SessionMessage, build_transcript_text

    transcript = build_transcript_text(
        [
            SessionMessage(role="user", title="You", body="What is Python GIL?"),
            SessionMessage(role="assistant", title="SeekFlow", body="The GIL is a CPython mutex."),
        ]
    )

    assert "You" in transcript
    assert "SeekFlow" in transcript
    assert "What is Python GIL?" in transcript
    assert "The GIL is a CPython mutex." in transcript
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_formatter.py -v`
Expected: FAIL because `build_header_text` and `build_transcript_text` do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def build_header_text(config) -> str:
    return "\n".join(
        [
            "SeekFlow",
            "Welcome back!",
            f"provider: {config.app.default_provider}",
            f"model: {config.llm.model}",
        ]
    )


def build_transcript_text(messages: list[SessionMessage]) -> str:
    if not messages:
        return 'System\nTry "compare asyncio vs threading in Python"'
    return "\n\n".join(f"{message.title}\n{message.body}" for message in messages[-10:])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_formatter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_formatter.py src/seekflow/output/formatter.py
git commit -m "feat: add tui text formatters"
```

### Task 2: Add prompt-toolkit TUI application wrapper

**Files:**
- Modify: `src/seekflow/repl/session.py`
- Test: `tests/test_repl.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_create_repl_view_returns_text_sections(app_config) -> None:
    from seekflow.output.formatter import SessionMessage
    from seekflow.repl.session import build_repl_view

    sections = build_repl_view(
        app_config,
        [SessionMessage(role="assistant", title="SeekFlow", body="hello")],
        "draft input",
    )

    assert "SeekFlow" in sections["header"]
    assert "hello" in sections["transcript"]
    assert "draft input" in sections["input"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repl.py -v`
Expected: FAIL because `build_repl_view` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def build_repl_view(config, messages, current_input: str) -> dict[str, str]:
    return {
        "header": build_header_text(config),
        "transcript": build_transcript_text(messages),
        "input": current_input,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_repl.py src/seekflow/repl/session.py
git commit -m "feat: add prompt toolkit repl view model"
```

### Task 3: Replace prompt_async loop with persistent prompt-toolkit TUI

**Files:**
- Modify: `src/seekflow/cli.py`
- Modify: `src/seekflow/repl/session.py`
- Modify: `src/seekflow/output/formatter.py`
- Test: `tests/test_repl.py`

- [ ] **Step 1: Write the failing test**

```python
def test_streaming_updates_assistant_message_without_console_clear() -> None:
    from seekflow.output.formatter import SessionMessage
    from seekflow.repl.session import append_stream_chunk

    messages: list[SessionMessage] = []

    append_stream_chunk(messages, "Hello")
    append_stream_chunk(messages, " world")

    assert messages[-1].role == "assistant"
    assert messages[-1].body == "Hello world"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repl.py -v`
Expected: FAIL because `append_stream_chunk` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def append_stream_chunk(messages: list[SessionMessage], chunk: str) -> SessionMessage:
    if not messages or messages[-1].role != "assistant":
        messages.append(SessionMessage(role="assistant", title="SeekFlow", body=""))
    messages[-1].body += chunk
    return messages[-1]
```

Then wire the REPL application so the chunk handler updates state and refreshes the prompt-toolkit transcript region instead of calling `render_app_shell()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_repl.py src/seekflow/repl/session.py src/seekflow/cli.py src/seekflow/output/formatter.py
git commit -m "feat: switch repl to persistent prompt toolkit tui"
```

### Task 4: Verify full behavior and remove flashing path from interactive flow

**Files:**
- Modify: `src/seekflow/cli.py`
- Modify: `src/seekflow/output/formatter.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_formatter.py`
- Test: `tests/test_repl.py`

- [ ] **Step 1: Write the failing regression assertion**

```python
def test_render_app_shell_still_builds_static_shell(app_config) -> None:
    from seekflow.output.formatter import SessionMessage, build_app_shell

    shell = build_app_shell(app_config, [SessionMessage(role="assistant", title="SeekFlow", body="ok")])

    assert shell is not None
```

Add or adjust tests so the static shell helper still works for non-interactive rendering while the interactive path uses prompt-toolkit-only updates.

- [ ] **Step 2: Run targeted tests to verify gaps**

Run: `pytest tests/test_cli.py tests/test_formatter.py tests/test_repl.py -v`
Expected: FAIL only where the new interactive path is not wired correctly.

- [ ] **Step 3: Write minimal implementation**

```python
# Keep build_app_shell for static rendering support.
# Remove console.clear() from the interactive path.
# Ensure run_repl uses the prompt-toolkit app lifecycle and not prompt_async() redraws.
```

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `pytest tests/test_cli.py tests/test_formatter.py tests/test_repl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli.py tests/test_formatter.py tests/test_repl.py src/seekflow/cli.py src/seekflow/output/formatter.py src/seekflow/repl/session.py
git commit -m "fix: remove flashing redraws from interactive repl"
```
