"""
Maps a classified query type to the corpora that should be searched.

Each query type has a primary source (most likely to answer the question)
plus one or two secondary sources, because real engineering questions
usually need more than one kind of evidence -- e.g. a troubleshooting
question benefits from incident history *and* the code that caused it.

On a retry loop (see graph/nodes.py::rewrite_query_node), the router widens
to ALL_SOURCES so a second attempt isn't limited by a possibly-wrong initial
classification.
"""
from __future__ import annotations

from typing import List

ALL_SOURCES = ["code", "docs", "architecture", "incidents"]

ROUTES = {
    "code": ["code", "docs"],
    "docs": ["docs", "code"],
    "architecture": ["architecture", "code"],
    "incidents": ["incidents", "code", "architecture"],
    "general": ALL_SOURCES,
}


def sources_for_query_type(query_type: str, widen: bool = False) -> List[str]:
    if widen:
        return ALL_SOURCES
    return ROUTES.get(query_type, ALL_SOURCES)
