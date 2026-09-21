from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Chunk:
    """A single retrievable unit of text plus its metadata."""

    text: str
    source_type: str  # "code" | "docs" | "architecture" | "incidents"
    source_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.source_type}:{self.source_path}:{self.metadata.get('chunk_index', 0)}"
