# SeekFlow

SeekFlow is a Python CLI that searches the web through pluggable providers, synthesizes cited answers with an OpenAI-compatible LLM, and saves results as a local Markdown knowledge base.

## Status

SeekFlow is currently an MVP.

Implemented in the current version:

- Interactive REPL-based CLI
- Pluggable search providers
  - DuckDuckGo
  - Brave Search API
  - SerpAPI
  - Playwright browser search
- Shared web content extraction pipeline
- OpenAI-compatible answer synthesis
- Local Markdown knowledge base persistence
- Slash commands for provider and KB management

Not implemented yet:

- `/config set`
- Provider auto-failover
- Semantic search or vector retrieval
- PDF/video/social-media extraction
- Full TUI knowledge-base browser

## Features

- Ask natural-language questions from a terminal REPL
- Switch between multiple search providers
- Generate cited answers with an OpenAI-compatible model
- Save each successful result as a Markdown note
- Browse, search, show, and delete saved KB entries
- Optional Obsidian-friendly frontmatter mode

## Installation

### Core install

```bash
pip install -e .
```

### Optional Playwright provider

```bash
pip install -e .[browser]
playwright install chromium
```

## Quick Start

### 1. Initialize config

```bash
seekflow init
```

This creates the default config file at:

```text
~/.seekflow/config.toml
```

### 2. Configure your LLM

The easiest way is environment variables:

```bash
export SEEKFLOW_LLM_API_KEY="your-api-key"
export SEEKFLOW_LLM_BASE_URL="https://api.openai.com/v1"
export SEEKFLOW_LLM_MODEL="gpt-4o-mini"
```

### 3. Start the REPL

```bash
seekflow
```

Example:

```text
seekflow> What is Python GIL?
```

## Commands

Current slash commands:

- `/help`
- `/provider list`
- `/provider switch <name>`
- `/provider status`
- `/kb list`
- `/kb search <query>`
- `/kb show <path>`
- `/kb delete <path>`
- `/config show`
- `/exit`
- `/quit`

## Knowledge Base Layout

By default, entries are stored under:

```text
~/.seekflow/knowledge/YYYY-MM/category/slug.md
```

Each file contains:

- YAML frontmatter
- `## Answer`
- `## Sources`

## Configuration

Default config structure:

```toml
[llm]
api_key = ""
base_url = "https://api.openai.com/v1"
model = "gpt-4o-mini"

[app]
default_provider = "duckduckgo"
max_results = 5
extract_top_n = 3

[knowledge_base]
kb_dir = "~/.seekflow/knowledge"
obsidian_mode = false
obsidian_vault_path = ""
obsidian_subfolder = "SeekFlow"
```

## Documentation

- Architecture: [docs/seekflow-architecture.md](docs/seekflow-architecture.md)
- Usage guide: [docs/seekflow-usage.md](docs/seekflow-usage.md)

## Development

Run the test suite:

```bash
pytest tests/ -v
```

## License

MIT. See [LICENSE](LICENSE).
