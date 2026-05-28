# SeekFlow Prompt Toolkit TUI Redesign

## Goal

Replace the current REPL rendering path that clears and redraws the full terminal on every streamed chunk with a persistent `prompt_toolkit` TUI that keeps a fixed header, a scrollable message stream, and a fixed input box.

## Problem

The current REPL flashes during streaming because each chunk triggers a full redraw:

- `on_chunk()` appends text and immediately redraws.
- `render_app_shell()` clears the whole terminal before printing the full UI.

This makes token streaming visually unstable compared with tools like Claude Code or Codex, which keep a persistent terminal UI and update only the changing regions.

## Scope

In scope:

- Replace the current `Rich` full-screen redraw approach for the interactive REPL.
- Keep a simplified welcome/status header inspired by Claude Code.
- Keep a scrollable conversation area.
- Keep a fixed bottom input area.
- Preserve existing command routing, chat/search routing, error handling, source display, and saved-entry notifications.

Out of scope:

- Reworking provider logic, routing logic, or synthesis logic.
- Adding mouse interactions or advanced key bindings beyond what is needed for the new TUI.
- Changing CLI subcommands like `seekflow init` or `seekflow --help`.

## Design

### Architecture

The REPL will become a persistent `prompt_toolkit` application with three vertically stacked regions:

1. Header region
   - Read-only formatted text showing version, provider, model, knowledge base path, recent activity, and one short tip.
   - Styled as a simplified framed welcome card.

2. Message region
   - Read-only scrollable text area containing the rendered conversation transcript.
   - Assistant streaming updates append to the in-memory message state and then update only this region.

3. Input region
   - Editable multiline input buffer fixed at the bottom.
   - `Enter` submits when appropriate and preserves the current REPL command/search dispatch behavior.

### Rendering Model

- `prompt_toolkit` owns the screen for the whole REPL session.
- UI text is derived from `SessionMessage` state and header state.
- No `console.clear()` calls remain in the interactive path.
- No full-screen `console.print()` redraw loop remains in the interactive path.
- Streaming updates trigger targeted UI invalidation rather than terminal clearing.

### Message Formatting

- Existing `SessionMessage` remains the core message model.
- A formatter layer converts messages into prompt-toolkit formatted text.
- Role labels remain visible: user, assistant, router, web search, error, sources, saved.
- Sources remain text-based rather than rich panels.

### Streaming Behavior

- `on_chunk()` still receives each chunk from chat or synthesis streams.
- The active assistant message is updated in memory.
- UI refresh is throttled lightly to avoid refreshing on every token burst.
- Final message content remains identical to the accumulated stream.

### Input Behavior

- Slash commands still route to the command handler.
- Normal text still routes to the search/chat path.
- `/exit` and `/quit` still leave the REPL.

## Testing

The redesign will be validated with automated tests for:

- Header rendering text contains key session information.
- Transcript rendering text contains role labels and message bodies.
- Streaming update state changes no longer rely on `console.clear()`.
- Existing CLI command behavior remains unchanged.

## Risks

- `prompt_toolkit` layout and multiline input behavior may require a small amount of iteration.
- Header layout will be simpler than the current `Rich` panel composition to keep the implementation focused.
- Terminal appearance may vary slightly by width, but should remain stable and non-flashing.
