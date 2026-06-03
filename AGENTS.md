# Repository Guidelines

## Project Structure & Module Organization

SeekFlow uses a `src/` layout. Application code lives in `src/seekflow/`, with modules split by responsibility: `cli.py` for the Typer entrypoint, `repl/` for interactive session behavior, `providers/` for search backends, `pipeline.py` for orchestration, `knowledge/` for Markdown persistence, `synthesis/` for LLM calls, and `output/` for terminal rendering. Tests live under `tests/`, including provider-specific tests in `tests/test_providers/`. End-user docs are in `docs/`.

## Build, Test, and Development Commands

- `pip install -e .` — install SeekFlow in editable mode.
- `pip install -e .[browser]` — install optional Playwright support.
- `seekflow --version` — verify the CLI entrypoint is available.
- `seekflow init` — create the local config file.
- `pytest tests/ -v` — run the full test suite.
- `python -m seekflow` — run the CLI module directly during development.

## Coding Style & Naming Conventions

Use Python 3.11+ conventions, 4-space indentation, and type hints on public functions. Prefer small, single-purpose modules over large files. Use `snake_case` for functions, variables, and module names; use `PascalCase` for classes and dataclasses such as `SearchPipeline` or `ProviderConfig`. Follow existing patterns: dataclasses in `models.py`, custom exceptions in `errors.py`, and async functions for network-bound work.

## Testing Guidelines

Tests use `pytest` and `pytest-asyncio`. Add or update tests before changing behavior, especially for CLI flow, provider adapters, pipeline orchestration, and terminal UI rendering. Name files `test_<feature>.py` and keep one main behavior per test where possible. Run focused tests during iteration, for example: `pytest tests/test_pipeline.py -v`.

## Commit & Pull Request Guidelines

Recent history uses short imperative subjects, usually Conventional Commit style, for example `feat: initial SeekFlow MVP` and `merge remote initial files`. Prefer `feat:`, `fix:`, `docs:`, and `refactor:` prefixes. 

After each feature implementation or code change, use the `requesting-code-review` skill against the current diff, apply fixes, and repeat the review/fix cycle until the review no longer reports any `Critical` or `Important` issues. Only then stage the files related to that change and prepare a concise commit message.

For every non-merge commit with staged file changes, automatically analyze the staged changes and generate the commit message. Keep the total commit message length within 20 lines. Keep the subject short, and list modified, fixed, or newly added items in the body using `-` bullet points instead of long paragraphs. For merge, revert, or other commits without a normal staged diff summary, use a short manual summary instead.

PRs should include a concise summary, test evidence (`pytest tests/ -v`), and screenshots or terminal captures for UI/REPL changes.

## Security & Configuration Tips

Do not commit local config, API keys, `.seekflow/`, `.seekflow-test/`, or `.sisyphus/`. Keep sensitive configuration in environment variables such as `SEEKFLOW_LLM_API_KEY`. When testing REPL changes, use `SEEKFLOW_CONFIG_PATH` to isolate local state.
