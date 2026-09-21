"""
A small, dependency-light vector store.

Why not FAISS/Chroma? Both are great and this project can be pointed at
either later, but this system deliberately supports a swappable TF-IDF
embedder whose dimensionality is only known after fitting on the corpus.
A tiny numpy-based cosine-similarity store keeps that swap trivial and the
whole thing inspectable in about 100 lines, with no native extensions to
compile. For a larger corpus than this demo, swap this module for FAISS
(`langchain_community.vectorstores.FAISS`) with the same Embedder interface.

Each source type (code / docs / architecture / incidents) gets its own
persisted collection so the LangGraph router can query exactly the source
types relevant to a question.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import List, Tuple

import numpy as np

from src.ingestion import Chunk


class SimpleVectorStore:
    def __init__(self, name: str):
        self.name = name
        self.chunks: List[Chunk] = []
        self.embeddings: np.ndarray | None = None  # shape (n, dim), L2-normalized

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def build(self, chunks: List[Chunk], embeddings: np.ndarray) -> None:
        assert len(chunks) == embeddings.shape[0], "chunks/embeddings length mismatch"
        self.chunks = chunks
        self.embeddings = self._normalize(embeddings)

    def search(self, query_embedding: np.ndarray, top_k: int = 4) -> List[Tuple[Chunk, float]]:
        if self.embeddings is None or len(self.chunks) == 0:
            return []
        q = self._normalize(query_embedding.reshape(1, -1))
        # Cosine similarity via dot product on L2-normalized vectors.
        # Guard against dimension mismatch (e.g. TF-IDF vocab changed).
        if q.shape[1] != self.embeddings.shape[1]:
            return []
        scores = (self.embeddings @ q.T).flatten()
        top_k = min(top_k, len(scores))
        top_idx = np.argpartition(-scores, top_k - 1)[:top_k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        return [(self.chunks[i], float(scores[i])) for i in top_idx]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "embeddings.npy", self.embeddings)
        with open(directory / "chunks.pkl", "wb") as f:
            pickle.dump(self.chunks, f)
        with open(directory / "meta.json", "w") as f:
            json.dump({"name": self.name, "count": len(self.chunks)}, f)

    @classmethod
    def load(cls, directory: Path) -> "SimpleVectorStore":
        meta = json.loads((directory / "meta.json").read_text())
        store = cls(meta["name"])
        store.embeddings = np.load(directory / "embeddings.npy")
        with open(directory / "chunks.pkl", "rb") as f:
            store.chunks = pickle.load(f)
        return store

    def __len__(self) -> int:
        return len(self.chunks)
