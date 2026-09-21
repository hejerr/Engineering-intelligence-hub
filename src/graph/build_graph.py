"""
Wires the nodes from graph/nodes.py into an actual LangGraph StateGraph.

Graph shape:

    classify_query -> retrieve -> generate_answer -> grade_answer
                                                         |
                                          needs_more_context?
                                            /            \\
                                          yes             no
                                           |               |
                                     rewrite_query      finalize -> END
                                           |
                                        retrieve   (loop back)

This is the part that specifically needs LangGraph rather than a plain
linear chain: the grade_answer -> rewrite_query -> retrieve cycle is a
genuine loop with a conditional exit, bounded by max_iterations so it can
never spin forever.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.nodes import build_nodes
from src.graph.state import HubState
from src.llm.client import LLMClient, get_llm_client
from src.retrieval.retrievers import HubRetriever


def build_graph(retriever: HubRetriever | None = None, llm_client: LLMClient | None = None):
    retriever = retriever or HubRetriever()
    llm_client = llm_client or get_llm_client()
    nodes = build_nodes(retriever, llm_client)

    graph = StateGraph(HubState)
    graph.add_node("classify_query", nodes["classify_query"])
    graph.add_node("retrieve", nodes["retrieve"])
    graph.add_node("generate_answer", nodes["generate_answer"])
    graph.add_node("grade_answer", nodes["grade_answer"])
    graph.add_node("rewrite_query", nodes["rewrite_query"])
    graph.add_node("finalize", nodes["finalize"])

    graph.set_entry_point("classify_query")
    graph.add_edge("classify_query", "retrieve")
    graph.add_edge("retrieve", "generate_answer")
    graph.add_edge("generate_answer", "grade_answer")
    graph.add_conditional_edges(
        "grade_answer",
        nodes["should_continue"],
        {"retry": "rewrite_query", "finalize": "finalize"},
    )
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("finalize", END)

    return graph.compile()
