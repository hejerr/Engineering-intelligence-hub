"""Loads the technical documentation corpus: real FastAPI markdown docs."""
from __future__ import annotations

from pathlib import Path
from typing import List

import config
from src.ingestion import Chunk
from src.ingestion.chunking import chunk_markdown


def load_docs_chunks(root: Path | None = None) -> List[Chunk]:
    root = root or config.CORPORA["docs"]
    chunks: List[Chunk] = []
    if not root.exists():
        return chunks

    for path in sorted(root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel_path = str(path.relative_to(root))
        file_chunks = chunk_markdown(text, source_path=rel_path, source_type="docs")
        for c in file_chunks:
            c.metadata["doc_file"] = rel_path
        chunks.extend(file_chunks)
    return chunks
