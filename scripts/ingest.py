#!/usr/bin/env python3
"""
Builds the retrieval index from everything under data/raw/.

Usage:
    python scripts/ingest.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.retrieval.retrievers import build_index  # noqa: E402


def main():
    start = time.time()
    print("Building Engineering Intelligence Hub index...\n")
    build_index(verbose=True)
    print(f"\nDone in {time.time() - start:.1f}s.")


if __name__ == "__main__":
    main()
