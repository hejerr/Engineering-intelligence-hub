"""Loads the incident-report corpus (real closed GitHub issues, see
scripts/fetch_incidents.py for provenance)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

import config
from src.ingestion import Chunk
from src.ingestion.chunking import chunk_markdown

_ISSUE_NUM_RE = re.compile(r"^(\d+)-")


def load_incident_chunks(root: Path | None = None) -> List[Chunk]:
    root = root or config.CORPORA["incidents"]
    chunks: List[Chunk] = []
    if not root.exists():
        return chunks

    for path in sorted(root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel_path = str(path.relative_to(root))
        file_chunks = chunk_markdown(text, source_path=rel_path, source_type="incidents")
        issue_match = _ISSUE_NUM_RE.match(path.name)
        for c in file_chunks:
            c.metadata["incident_file"] = rel_path
            if issue_match:
                c.metadata["issue_number"] = issue_match.group(1)
        chunks.extend(file_chunks)
    return chunks
