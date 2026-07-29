from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Artifact:
    name: str
    payload: Any
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BackendBinding:
    kind: str
    target: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StepSpec:
    name: str
    role: str
    consumes: str | None
    produces: str
    backend: BackendBinding | None = None


@dataclass(slots=True)
class WorkflowSpec:
    name: str
    steps: list[StepSpec]
