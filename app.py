"""
Optional interactive UI for the Engineering Intelligence Hub.

Not required to use the system (the CLI in scripts/ask.py is the primary
interface), but handy for demos.

Run with:
    pip install streamlit
    streamlit run app.py
"""
import re
import time

import streamlit as st

from src.graph.build_graph import build_graph
import config

st.set_page_config(page_title="Engineering Intelligence Hub", page_icon="🛠️", layout="wide")

st.title("🛠️ Engineering Intelligence Hub")
st.caption(
    "A LangGraph-powered RAG system over real FastAPI source code, documentation, "
    "authored architecture notes, and real closed GitHub issues used as incident reports."
)

with st.sidebar:
    st.subheader("Current configuration")
    st.write(f"**Embedding provider:** `{config.EMBEDDING_PROVIDER}`")
    st.write(f"**LLM provider:** `{config.LLM_PROVIDER}`")
    st.write(f"**Confidence threshold:** {config.CONFIDENCE_THRESHOLD}")
    st.write(f"**Max retry iterations:** {config.MAX_GRAPH_ITERATIONS}")
    if config.LLM_PROVIDER == "mock":
        st.info(
            "Running in offline MOCK mode. Set LLM_PROVIDER=anthropic or "
            "openai (and the matching API key) in `.env` for real answers."
        )


@st.cache_resource
def get_app():
    return build_graph()


_ISSUE_NUM_RE = re.compile(r"^(\d+)-")


def source_link(source_type: str, source_path: str) -> str | None:
    """Best-effort link back to the real, public source of a citation.
    Returns None for authored content (architecture notes) that has no
    public URL of its own. Note: the FastAPI project moved from
    github.com/tiangolo/fastapi to github.com/fastapi/fastapi; we link to
    the current canonical location."""
    if source_type == "code":
        # source_path already looks like "fastapi/routing.py", matching
        # the real repo's layout exactly.
        return f"https://github.com/fastapi/fastapi/blob/master/{source_path}"
    if source_type == "docs":
        # source_path looks like "fastapi_docs/advanced/sub-applications.md";
        # the real repo has these under docs/en/docs/ instead of fastapi_docs/.
        relative = source_path.split("/", 1)[1] if "/" in source_path else source_path
        return f"https://github.com/fastapi/fastapi/blob/master/docs/en/docs/{relative}"
    if source_type == "incidents":
        match = _ISSUE_NUM_RE.match(source_path)
        if match:
            return f"https://github.com/fastapi/fastapi/issues/{match.group(1)}"
    return None


question = st.text_input(
    "Ask an engineering question",
    placeholder="e.g. Why would a mounted sub-application not run my middleware?",
)

if st.button("Ask", type="primary") and question:
    graph_app = get_app()
    start = time.time()
    with st.spinner("Routing, retrieving, and grading..."):
        result = graph_app.invoke({"question": question})
    elapsed = time.time() - start

    col1, col2, col3 = st.columns(3)
    col1.metric("Classified as", result.get("query_type", "?"))
    col2.metric("Confidence", f"{result.get('confidence', 0):.2f}")
    col3.metric("Time", f"{elapsed:.1f}s")

    st.markdown("### Answer")
    st.markdown(result.get("draft_answer", ""))

    # --- "How I got this answer" — makes the routing + retry decisions
    # visible instead of hiding them behind a normal-looking chat answer.
    iterations_used = result.get("iteration", 0) + 1
    did_retry = result.get("iteration", 0) > 0
    tried_sources = result.get("tried_source_types", [])

    with st.expander("🔍 How I got this answer", expanded=False):
        st.markdown(
            f"**1. Classified this as an `{result.get('query_type', '?')}` question**, "
            f"so it searched: `{'`, `'.join(tried_sources) or 'none'}`"
        )
        if did_retry:
            st.markdown(
                f"**2. First attempt wasn't confident enough** "
                f"({result.get('grade_reason', 'no reason recorded')}), "
                f"so it broadened the search and tried again."
            )
            st.markdown(
                f"**3. Used {iterations_used} of {config.MAX_GRAPH_ITERATIONS + 1} "
                f"allowed attempts**, ending at confidence "
                f"**{result.get('confidence', 0):.2f}**."
            )
        else:
            st.markdown(
                f"**2. The first search was confident enough** "
                f"(**{result.get('confidence', 0):.2f}**, above the "
                f"{config.CONFIDENCE_THRESHOLD} threshold), so it answered "
                f"immediately without retrying."
            )
        st.caption(
            "This project's core idea: route to the right sources first, "
            "then double-check confidence and retry only when needed — "
            "instead of searching everything, every time."
        )

    st.markdown("### Sources")
    for s in result.get("sources", [])[:10]:
        link = source_link(s["source_type"], s["source_path"])
        label = f"[{s['source_type']}] {s['source_path']}  (relevance {s['score']})"
        with st.expander(label):
            if link:
                st.markdown(f"[View the real source on GitHub ↗]({link})")
            st.code(s["snippet"])

