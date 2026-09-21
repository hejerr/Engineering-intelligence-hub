"""
Builds and loads the full multi-collection index, and exposes a single
retriever object the LangGraph nodes use to fetch context by source type.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import config
from src.ingestion import Chunk
from src.ingestion.architecture_loader import load_architecture_chunks
from src.ingestion.code_loader import load_code_chunks
from src.ingestion.docs_loader import load_docs_chunks
from src.ingestion.incident_loader import load_incident_chunks
from src.retrieval.embeddings import get_embedder
from src.retrieval.vectorstore import SimpleVectorStore

LOADERS = {
    "code": load_code_chunks,
    "docs": load_docs_chunks,
    "architecture": load_architecture_chunks,
    "incidents": load_incident_chunks,
}


def build_index(verbose: bool = True, provider: str | None = None, store_dir=None) -> None:
    """Loads every corpus, fits one shared embedder, builds one vector store
    per source type, and persists everything under `store_dir` (defaults to
    config.VECTOR_STORE_DIR). `provider` overrides config.EMBEDDING_PROVIDER
    without touching the environment -- used by scripts/eval_embeddings.py
    to build a second, separate index for comparison."""
    store_dir = store_dir or config.VECTOR_STORE_DIR
    provider = provider or config.EMBEDDING_PROVIDER

    all_chunks: Dict[str, List[Chunk]] = {}
    for source_type, loader in LOADERS.items():
        chunks = loader()
        all_chunks[source_type] = chunks
        if verbose:
            print(f"[ingest] {source_type}: {len(chunks)} chunks")

    flat_chunks = [c for chunks in all_chunks.values() for c in chunks]
    if not flat_chunks:
        raise RuntimeError(
            "No chunks were loaded from data/raw/*. Did you run the data "
            "collection steps described in README.md?"
        )

    embedder = get_embedder(provider)
    embedder.fit([c.text for c in flat_chunks])

    store_dir.mkdir(parents=True, exist_ok=True)
    with open(store_dir / "embedder.pkl", "wb") as f:
        pickle.dump({"provider": provider, "embedder": embedder}, f)

    for source_type, chunks in all_chunks.items():
        store = SimpleVectorStore(name=source_type)
        if chunks:
            embeddings = embedder.embed([c.text for c in chunks])
            store.build(chunks, embeddings)
        store.save(store_dir / source_type)
        if verbose:
            print(f"[ingest] saved '{source_type}' collection ({len(store)} chunks)")


class HubRetriever:
    """Loads the persisted index and answers retrieval queries scoped to
    one or more source types."""

    def __init__(self, store_dir: Path | None = None):
        store_dir = store_dir or config.VECTOR_STORE_DIR
        embedder_path = store_dir / "embedder.pkl"
        if not embedder_path.exists():
            raise FileNotFoundError(
                f"No index found at {store_dir}. Run `python scripts/ingest.py` first."
            )
        with open(embedder_path, "rb") as f:
            payload = pickle.load(f)
        self.embedder = payload["embedder"]

        self.stores: Dict[str, SimpleVectorStore] = {}
        for source_type in LOADERS:
            collection_dir = store_dir / source_type
            if collection_dir.exists():
                self.stores[source_type] = SimpleVectorStore.load(collection_dir)

    def retrieve(
        self, query: str, source_types: List[str], top_k: int | None = None
    ) -> List[Tuple[Chunk, float]]:
        top_k = top_k or config.TOP_K_PER_SOURCE
        query_embedding = self.embedder.embed([query])[0]

        results: List[Tuple[Chunk, float]] = []
        for source_type in source_types:
            store = self.stores.get(source_type)
            if store is None:
                continue
            results.extend(store.search(query_embedding, top_k=top_k))

        results.sort(key=lambda pair: pair[1], reverse=True)
        return results

    def available_sources(self) -> List[str]:
        return [name for name, store in self.stores.items() if len(store) > 0]
