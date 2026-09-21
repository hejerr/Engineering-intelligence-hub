"""
Chunking strategies.

Code and prose need different splitting strategies:

  - Code is split by line windows (simple, robust across any language) with
    a small overlap so a function that straddles a chunk boundary is still
    findable from either side.
  - Markdown/prose is split on header boundaries first (so a chunk stays
    within one logical section), then further split by character budget if
    a section is too long.
"""
from __future__ import annotations

import re
from typing import List

import config
from src.ingestion import Chunk


def chunk_code(text: str, source_path: str, source_type: str = "code") -> List[Chunk]:
    lines = text.splitlines()
    if not lines:
        return []

    max_lines = config.CODE_CHUNK_MAX_LINES
    overlap = config.CODE_CHUNK_OVERLAP_LINES
    step = max(max_lines - overlap, 1)

    chunks: List[Chunk] = []
    idx = 0
    chunk_index = 0
    while idx < len(lines):
        window = lines[idx : idx + max_lines]
        body = "\n".join(window)
        if body.strip():
            chunks.append(
                Chunk(
                    text=body,
                    source_type=source_type,
                    source_path=source_path,
                    metadata={
                        "chunk_index": chunk_index,
                        "start_line": idx + 1,
                        "end_line": idx + len(window),
                    },
                )
            )
            chunk_index += 1
        idx += step
    return chunks


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def _split_by_headers(text: str) -> List[str]:
    """Split markdown into sections, each starting at a header line."""
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        return [text]

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(text[start:end])

    # Keep any preamble before the first header
    if matches[0].start() > 0:
        sections.insert(0, text[: matches[0].start()])

    return [s for s in sections if s.strip()]


def _split_by_chars(text: str, max_chars: int, overlap: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    step = max(max_chars - overlap, 1)
    return [text[i : i + max_chars] for i in range(0, len(text), step) if text[i : i + max_chars].strip()]


def chunk_markdown(text: str, source_path: str, source_type: str) -> List[Chunk]:
    max_chars = config.TEXT_CHUNK_MAX_CHARS
    overlap = config.TEXT_CHUNK_OVERLAP_CHARS

    sections = _split_by_headers(text)
    chunks: List[Chunk] = []
    chunk_index = 0
    for section in sections:
        header_match = _HEADER_RE.match(section.strip())
        section_title = header_match.group(2) if header_match else None
        for piece in _split_by_chars(section, max_chars, overlap):
            chunks.append(
                Chunk(
                    text=piece.strip(),
                    source_type=source_type,
                    source_path=source_path,
                    metadata={"chunk_index": chunk_index, "section": section_title},
                )
            )
            chunk_index += 1
    return chunks
