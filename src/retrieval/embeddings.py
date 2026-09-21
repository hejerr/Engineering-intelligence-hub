"""
Pluggable embedding backends.

All backends implement the same tiny interface:

    fit(texts: List[str]) -> None          # only meaningful for tfidf
    embed(texts: List[str]) -> np.ndarray  # shape (n_texts, dim)

Select the backend with the EMBEDDING_PROVIDER env var (see config.py).
Default is "tfidf" so the whole project runs offline with zero downloads.
"""
from __future__ import annotations

from typing import List, Protocol

import numpy as np

import config


class Embedder(Protocol):
    def fit(self, texts: List[str]) -> None: ...
    def embed(self, texts: List[str]) -> np.ndarray: ...


class TfidfEmbedder:
    """Local, deterministic, no downloads. Good default for a portfolio
    project or any environment without internet access to model hubs."""

    def __init__(self, max_features: int = 20000):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            stop_words="english",
        )
        self._fitted = False

    def fit(self, texts: List[str]) -> None:
        self.vectorizer.fit(texts)
        self._fitted = True

    def embed(self, texts: List[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("TfidfEmbedder.fit() must be called before embed()")
        matrix = self.vectorizer.transform(texts)
        return matrix.toarray().astype("float32")


class HuggingFaceEmbedder:
    """Local dense embeddings via sentence-transformers. Downloads the model
    from huggingface.co on first use, so it needs normal internet access."""

    def __init__(self, model_name: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name or config.HUGGINGFACE_EMBEDDING_MODEL)

    def fit(self, texts: List[str]) -> None:
        pass  # dense embedding models don't need fitting

    def embed(self, texts: List[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, show_progress_bar=False), dtype="float32")


class OpenAIEmbedder:
    """OpenAI embeddings API. Requires OPENAI_API_KEY."""

    def __init__(self, model_name: str | None = None):
        from openai import OpenAI

        self.client = OpenAI()
        self.model_name = model_name or config.OPENAI_EMBEDDING_MODEL

    def fit(self, texts: List[str]) -> None:
        pass

    def embed(self, texts: List[str]) -> np.ndarray:
        # OpenAI's API accepts batches; keep batches modest to avoid limits.
        vectors = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = self.client.embeddings.create(model=self.model_name, input=batch)
            vectors.extend([d.embedding for d in resp.data])
        return np.asarray(vectors, dtype="float32")


def get_embedder(provider: str | None = None) -> Embedder:
    provider = provider or config.EMBEDDING_PROVIDER
    if provider == "tfidf":
        return TfidfEmbedder()
    if provider == "huggingface":
        return HuggingFaceEmbedder()
    if provider == "openai":
        return OpenAIEmbedder()
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")
