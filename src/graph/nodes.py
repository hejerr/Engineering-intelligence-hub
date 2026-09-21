"""
Node implementations for the Engineering Intelligence Hub graph.

Each node is a plain function `(state: HubState) -> dict` that returns only
the keys it wants to update -- this is the standard LangGraph pattern and
keeps every node independently testable.

Nodes are produced by `build_nodes(retriever, llm_client)` so the actual
retriever/LLM implementations are injected rather than imported globally --
this makes it trivial to swap in a mock retriever/LLM for unit tests.
"""
from __future__ import annotations

import re
from typing import Callable, Dict

import config
from src.graph.router import sources_for_query_type
from src.graph.state import HubState, SourceRef
from src.llm.client import LLMClient
from src.retrieval.retrievers import HubRetriever

VALID_QUERY_TYPES = {"code", "docs", "architecture", "incidents", "general"}

CLASSIFY_SYSTEM_PROMPT = """CLASSIFY_TASK
You are the routing brain of an engineering knowledge-hub RAG system.
Classify the user's question into exactly one label, and reply with ONLY
that label, nothing else:

- code          -> asking about a specific function/class/implementation detail
- docs          -> asking how to use a feature, a "how do I..." usage question
- architecture  -> asking how a system/subsystem is designed or how requests
                   flow through it
- incidents     -> troubleshooting, asking about a bug, error, or past failure
- general       -> broad onboarding questions, or anything that doesn't fit
                   cleanly into the above

Reply with exactly one of: code, docs, architecture, incidents, general
"""

GENERATE_SYSTEM_PROMPT = """You are an engineering knowledge assistant. Answer the
user's question using ONLY the retrieved context provided between
<context> tags. Every claim you make must be traceable to the context.

Rules:
- Cite sources inline like [source: <source_path>] right after each claim.
- If the context is insufficient to fully answer, say so explicitly instead
  of guessing.
- Prefer concrete, actionable detail (function names, file paths, exact
  steps) over vague summaries.
- Keep the answer focused and skimmable; use short paragraphs or bullets.
"""

GRADE_SYSTEM_PROMPT = """GRADE_ANSWER_TASK
You are grading whether a draft answer is well-supported by the retrieved
context. Reply in exactly this format:

CONFIDENCE: <a number between 0.0 and 1.0>
REASON: <one short sentence>

You will also be given TOP_SCORE: the retrieval system's own similarity
score between the question and its best-matching chunk (roughly 0 = no
real match at all, 0.2+ = a strong match). Treat a low TOP_SCORE as strong
evidence the retrieved context is unrelated to the question, regardless of
how the draft answer is worded.

Score LOW (0.2 or below) if any of these are true:
- the answer admits it could not find relevant information in the context
- the answer says the context does not address the question
- TOP_SCORE is low
- the answer seems to be guessing beyond what the context actually supports

Score HIGH (0.7+) only if the answer is concrete, specific, and clearly
grounded in context that is actually relevant to the question.

Important: a polished, honest "I don't know" or "the context doesn't cover
this" is NOT a high-confidence answer. It is a correctly LOW-confidence
result, because the system did not actually answer the question -- do not
reward it for being well-written.
"""

REWRITE_SYSTEM_PROMPT = """You rewrite search queries for a retrieval system
that didn't find enough relevant context on the first try. Given the
original question and what was tried, produce ONE improved search query
(broader terms, synonyms, or a rephrasing). Reply with ONLY the new query
text, nothing else.
"""


def _format_context(retrieved) -> tuple[str, list]:
    """Turns retrieved (Chunk, score) pairs into a single context string and
    a list of structured SourceRef dicts for the final citation list."""
    pieces = []
    sources: list[SourceRef] = []
    for chunk, score in retrieved:
        header = f"[{chunk.source_type}] {chunk.source_path}"
        pieces.append(f"{header}\n{chunk.text}")
        sources.append(
            SourceRef(
                source_type=chunk.source_type,
                source_path=chunk.source_path,
                score=round(float(score), 3),
                snippet=chunk.text[:220].strip(),
            )
        )
    context_text = "\n\n---\n\n".join(pieces)
    return context_text, sources


def build_nodes(retriever: HubRetriever, llm_client: LLMClient) -> Dict[str, Callable]:
    def classify_query_node(state: HubState) -> dict:
        question = state["question"]
        raw = llm_client.complete(CLASSIFY_SYSTEM_PROMPT, question).strip().lower()
        query_type = next((v for v in VALID_QUERY_TYPES if v in raw), "general")
        return {
            "query_type": query_type,
            "search_query": question,
            "iteration": 0,
            "max_iterations": state.get("max_iterations", config.MAX_GRAPH_ITERATIONS),
            "tried_source_types": [],
        }

    def retrieve_node(state: HubState) -> dict:
        widen = state.get("iteration", 0) > 0
        source_types = sources_for_query_type(state["query_type"], widen=widen)
        retrieved = retriever.retrieve(state["search_query"], source_types)
        context_text, sources = _format_context(retrieved)
        tried = list(set(state.get("tried_source_types", []) + source_types))
        return {
            "retrieved_chunks": retrieved,
            "context_text": context_text,
            "sources": sources,
            "tried_source_types": tried,
        }

    def generate_answer_node(state: HubState) -> dict:
        user_prompt = (
            f"<question>{state['question']}</question>\n\n"
            f"<context>{state.get('context_text', '')}</context>"
        )
        draft = llm_client.complete(GENERATE_SYSTEM_PROMPT, user_prompt)
        return {"draft_answer": draft}

    def grade_answer_node(state: HubState) -> dict:
        retrieved = state.get("retrieved_chunks") or []
        top_score = max((score for _, score in retrieved), default=0.0)
        user_prompt = (
            f"<question>{state['question']}</question>\n\n"
            f"<context>{state.get('context_text', '')}</context>\n\n"
            f"Draft answer:\n{state.get('draft_answer', '')}\n\n"
            f"TOP_SCORE: {top_score:.4f}"
        )
        raw = llm_client.complete(GRADE_SYSTEM_PROMPT, user_prompt)
        match = re.search(r"CONFIDENCE:\s*([0-9]*\.?[0-9]+)", raw)
        llm_confidence = float(match.group(1)) if match else 0.5
        llm_confidence = max(0.0, min(1.0, llm_confidence))
        reason_match = re.search(r"REASON:\s*(.*)", raw)
        reason = reason_match.group(1).strip() if reason_match else raw.strip()

        # Safety net: don't just trust the LLM's self-grading. A model can
        # grade a well-written "I don't know" as high-confidence, because
        # it *is* well-supported by an empty context -- but that isn't a
        # useful answer. Cap confidence by how much real retrieval evidence
        # actually backed it, independent of how convincing the wording is.
        retrieval_ceiling = min(1.0, 0.1 + top_score * 3.0)
        confidence = min(llm_confidence, retrieval_ceiling)
        if confidence < llm_confidence - 0.01:
            reason = f"{reason} (capped: top retrieval similarity was only {top_score:.3f})"

        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", config.MAX_GRAPH_ITERATIONS)
        needs_more = confidence < config.CONFIDENCE_THRESHOLD and iteration < max_iterations

        return {
            "confidence": confidence,
            "grade_reason": reason,
            "needs_more_context": needs_more,
        }

    def rewrite_query_node(state: HubState) -> dict:
        user_prompt = (
            f"<question>{state['question']}</question>\n"
            f"Original search query: {state.get('search_query', '')}\n"
            f"Sources already tried: {', '.join(state.get('tried_source_types', []))}\n"
            f"Reason retrieval was insufficient: {state.get('grade_reason', '')}"
        )
        if isinstance(llm_client, type(llm_client)) and llm_client.__class__.__name__ == "MockLLMClient":
            # Cheap, deterministic widening for the offline demo path.
            new_query = f"{state['question']} overview background context"
        else:
            new_query = llm_client.complete(REWRITE_SYSTEM_PROMPT, user_prompt).strip()

        return {
            "search_query": new_query or state["question"],
            "iteration": state.get("iteration", 0) + 1,
        }

    def finalize_node(state: HubState) -> dict:
        confidence = state.get("confidence", 0.0)
        sources = state.get("sources", [])
        draft = state.get("draft_answer", "")

        source_lines = "\n".join(
            f"  {i+1}. [{s['source_type']}] {s['source_path']} (relevance {s['score']})"
            for i, s in enumerate(sources[:8])
        ) or "  (no sources retrieved)"

        final = (
            f"{draft}\n\n"
            f"---\n"
            f"Confidence: {confidence:.2f}  |  Iterations used: {state.get('iteration', 0) + 1}\n"
            f"Sources:\n{source_lines}"
        )
        return {"final_answer": final}

    def should_continue(state: HubState) -> str:
        return "retry" if state.get("needs_more_context") else "finalize"

    return {
        "classify_query": classify_query_node,
        "retrieve": retrieve_node,
        "generate_answer": generate_answer_node,
        "grade_answer": grade_answer_node,
        "rewrite_query": rewrite_query_node,
        "finalize": finalize_node,
        "should_continue": should_continue,
    }
