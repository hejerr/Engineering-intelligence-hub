"""Loads the code corpus: real FastAPI source files under data/raw/code."""
from __future__ import annotations

from pathlib import Path
from typing import List

import config
from src.ingestion import Chunk
from src.ingestion.chunking import chunk_code

CODE_EXTENSIONS = {".py"}


def load_code_chunks(root: Path | None = None) -> List[Chunk]:
    root = root or config.CORPORA["code"]
    chunks: List[Chunk] = []
    if not root.exists():
        return chunks

    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in CODE_EXTENSIONS:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel_path = str(path.relative_to(root))
            file_chunks = chunk_code(text, source_path=rel_path, source_type="code")
            for c in file_chunks:
                c.metadata["language"] = "python"
                c.metadata["module"] = rel_path
            chunks.extend(file_chunks)
    return chunks
