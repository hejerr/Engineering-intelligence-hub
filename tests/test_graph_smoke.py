"""
End-to-end smoke test: runs the full LangGraph pipeline with the default
offline settings (EMBEDDING_PROVIDER=tfidf, LLM_PROVIDER=mock) so it needs
no API keys and no network access. Run with:

    python -m pytest tests/test_graph_smoke.py -v

or just:

    python tests/test_graph_smoke.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("EMBEDDING_PROVIDER", "tfidf")
os.environ.setdefault("LLM_PROVIDER", "mock")

import config  # noqa: E402
from src.retrieval.retrievers import build_index, HubRetriever  # noqa: E402
from src.graph.build_graph import build_graph  # noqa: E402


def test_index_builds_and_has_all_sources():
    if not (config.VECTOR_STORE_DIR / "embedder.pkl").exists():
        build_index(verbose=False)
    retriever = HubRetriever()
    sources = retriever.available_sources()
    assert "code" in sources
    assert "docs" in sources
    assert "architecture" in sources
    assert len(retriever.stores["code"]) > 0


def test_graph_runs_end_to_end_for_code_question():
    app = build_graph()
    result = app.invoke({"question": "How does FastAPI resolve dependencies with Depends()?"})
    assert "final_answer" in result
    assert result["query_type"] in {"code", "architecture", "general", "docs", "incidents"}
    assert result["confidence"] >= 0.0
    assert len(result["sources"]) > 0


def test_graph_runs_end_to_end_for_incident_question():
    app = build_graph()
    result = app.invoke(
        {"question": "There's a bug where background tasks lose headers with streaming responses, what happened?"}
    )
    assert "final_answer" in result
    assert len(result["final_answer"]) > 0


if __name__ == "__main__":
    test_index_builds_and_has_all_sources()
    print("test_index_builds_and_has_all_sources passed")
    test_graph_runs_end_to_end_for_code_question()
    print("test_graph_runs_end_to_end_for_code_question passed")
    test_graph_runs_end_to_end_for_incident_question()
    print("test_graph_runs_end_to_end_for_incident_question passed")
    print("\nAll smoke tests passed.")
