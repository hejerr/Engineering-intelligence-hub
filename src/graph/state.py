"""
The shared state that flows through every node in the LangGraph graph.

Using a single TypedDict keeps every node's signature simple (state in,
partial-state-update out) and makes the whole pipeline easy to trace/debug
--- print `state` at any point and you see everything that's happened.
"""
from __future__ import annotations

from typing import Any, List, Optional, TypedDict


class SourceRef(TypedDict):
    source_type: str
    source_path: str
    score: float
    snippet: str


class HubState(TypedDict, total=False):
    # Input
    question: str

    # Classification
    query_type: str  # "code" | "docs" | "architecture" | "incidents" | "general"

    # Retrieval
    search_query: str
    retrieved_chunks: List[Any]  # List[Tuple[Chunk, float]] for the current iteration
    context_text: str
    sources: List[SourceRef]

    # Generation + self-grading loop
    draft_answer: str
    confidence: float
    grade_reason: str
    needs_more_context: bool
    iteration: int
    max_iterations: int
    tried_source_types: List[str]

    # Output
    final_answer: str
