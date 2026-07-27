from __future__ import annotations

from collections.abc import Awaitable
from typing import Protocol

from seekflow.workflows.models import Artifact


class NativeStep(Protocol):
    def run(self, artifact: Artifact | None, context: dict) -> Artifact | Awaitable[Artifact]:
        ...
