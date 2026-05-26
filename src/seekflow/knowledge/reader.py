from pathlib import Path
import re

import yaml


def parse_frontmatter(file_path: Path) -> dict[str, object]:
    content = file_path.read_text()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def list_entries(kb_dir: Path) -> list[dict[str, object]]:
    return [
        {"file_path": path, **parse_frontmatter(path)}
        for path in sorted(kb_dir.glob("**/*.md"), reverse=True)
    ]


def search_entries(kb_dir: Path, query: str) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for path in kb_dir.glob("**/*.md"):
        content = path.read_text()
        if re.search(query, content, re.IGNORECASE):
            matches.append({"file_path": path, **parse_frontmatter(path)})
    return matches


def read_entry(file_path: Path) -> str:
    return file_path.read_text()


def delete_entry(file_path: Path) -> bool:
    if not file_path.exists():
        return False
    file_path.unlink()
    return True
