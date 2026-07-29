from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class WorkflowSessionState:
    latest_brief_entry: Any | None = None
    latest_outline_artifact: Any | None = None
    latest_article_artifact: Any | None = None
    latest_workflow_name: str | None = None
