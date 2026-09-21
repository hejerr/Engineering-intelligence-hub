#!/usr/bin/env python3
"""
Compares retrieval quality between the default local TF-IDF embeddings and
real dense embeddings via sentence-transformers (HuggingFace), using a
small hand-labeled set of (question, expected source file) pairs.

This builds two SEPARATE indices under data/processed/vector_store_<provider>/
so it never touches your main data/processed/vector_store/ used by ask.py.

Needs internet access to huggingface.co the first time it downloads the
sentence-transformers model -- run this on a machine with normal internet
access. (Not required for the rest of this project, which works fully
offline with the tfidf default.)

Usage:
    pip install sentence-transformers
    python scripts/eval_embeddings.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from src.retrieval.retrievers import build_index, HubRetriever  # noqa: E402

# Each question is paired with substrings that, if found in a retrieved
# chunk's source_path, count as a "correct" hit. Based on the real files
# under data/raw/docs and data/raw/architecture.
EVAL_SET = [
    ("How does FastAPI resolve nested dependencies?", ["dependencies/utils.py", "02-dependency-injection"]),
    ("How do I upload a file in a request?", ["request-files", "uploadfile"]),
    ("What happens when a mounted sub-app receives a request?", ["sub-applications", "03-routing-internals"]),
    ("How are query parameters validated with constraints?", ["query-params", "query-param-models"]),
    ("Why would background tasks lose headers with streaming?", ["background-tasks", "reference/background"]),
    ("What does response_model actually filter from the output?", ["response-model", "04-validation"]),
    ("How does route matching order affect path parameters?", ["03-routing-internals", "path-params"]),
    ("What's the difference between include_router and mounting an app?", ["03-routing-internals", "sub-applications"]),
    ("How is a Pydantic validation error turned into a 422 response?", ["04-validation", "handling-errors"]),
    ("How does per-request dependency caching work?", ["02-dependency-injection", "dependencies/utils.py"]),
]


def evaluate(retriever: HubRetriever, top_k: int = 5):
    hits = 0
    reciprocal_ranks = []
    details = []
    for question, expected_substrings in EVAL_SET:
        results = retriever.retrieve(
            question, source_types=["code", "docs", "architecture", "incidents"], top_k=top_k
        )
        rank = None
        for i, (chunk, _score) in enumerate(results, start=1):
            if any(sub in chunk.source_path for sub in expected_substrings):
                rank = i
                break
        if rank:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
        details.append((question, rank))

    hit_rate = hits / len(EVAL_SET)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    return hit_rate, mrr, details


def main():
    providers_to_try = ["tfidf", "huggingface"]
    all_results = {}

    for provider in providers_to_try:
        store_dir = config.DATA_PROCESSED_DIR / f"vector_store_{provider}"
        print(f"\nBuilding index with EMBEDDING_PROVIDER={provider}...")
        try:
            start = time.time()
            build_index(verbose=False, provider=provider, store_dir=store_dir)
            build_time = time.time() - start
        except Exception as e:
            print(f"  Skipped '{provider}': {type(e).__name__}: {e}")
            continue

        retriever = HubRetriever(store_dir=store_dir)
        hit_rate, mrr, details = evaluate(retriever)
        all_results[provider] = {"hit_rate@5": hit_rate, "mrr@5": mrr, "build_time_s": round(build_time, 1)}

        print(f"  Build time: {build_time:.1f}s")
        print(f"  Hit@5: {hit_rate:.2f}   MRR@5: {mrr:.3f}")
        for question, rank in details:
            status = f"rank {rank}" if rank else "NOT FOUND in top 5"
            print(f"    - {question[:55]:57s} {status}")

    print("\n=== Summary ===")
    if not all_results:
        print("  No providers ran successfully.")
        return
    for provider, metrics in all_results.items():
        print(
            f"  {provider:12s} Hit@5={metrics['hit_rate@5']:.2f}  "
            f"MRR@5={metrics['mrr@5']:.3f}  build={metrics['build_time_s']}s"
        )
    if "tfidf" in all_results and "huggingface" in all_results:
        mrr_delta = all_results["huggingface"]["mrr@5"] - all_results["tfidf"]["mrr@5"]
        print(f"\n  HuggingFace MRR@5 vs TF-IDF: {mrr_delta:+.3f}")


if __name__ == "__main__":
    main()
