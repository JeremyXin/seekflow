from pathlib import Path

import yaml
from slugify import slugify

from seekflow.models import KBEntry


def slugify_query(query: str) -> str:
    return slugify(query, max_length=60)


def render_markdown(entry: KBEntry, obsidian_mode: bool = False) -> str:
    frontmatter = {
        "title": entry.title,
        "date": entry.date.isoformat(),
        "query": entry.query,
        "summary": entry.summary,
        "tags": entry.tags,
        "category": entry.category,
        "provider": entry.provider,
        "model": entry.model,
        "source_urls": [item.url for item in entry.sources],
    }
    if obsidian_mode:
        frontmatter["aliases"] = []
        frontmatter["cssclasses"] = []
    header = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    sources = "\n".join(
        f"{idx}. [{item.title}]({item.url})" for idx, item in enumerate(entry.sources, start=1)
    )
    return f"---\n{header}\n---\n\n## Answer\n\n{entry.answer}\n\n## Sources\n\n{sources}\n"


def build_entry_path(kb_dir: Path, entry: KBEntry) -> Path:
    slug = slugify_query(entry.query)
    folder = kb_dir / entry.date.strftime("%Y-%m") / entry.category
    return folder / f"{slug}.md"


async def save_entry(entry: KBEntry, kb_dir: Path, obsidian_mode: bool = False) -> Path:
    path = build_entry_path(kb_dir, entry)
    counter = 2
    while path.exists():
        path = path.with_name(f"{path.stem}-{counter}.md")
        counter += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(entry, obsidian_mode=obsidian_mode))
    entry.file_path = path
    return path
