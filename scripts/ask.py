#!/usr/bin/env python3
"""
Ask a question through the LangGraph pipeline.

Usage:
    python scripts/ask.py "How does dependency injection caching work?"
    python scripts/ask.py --trace "Why would a mounted sub-app not run my middleware?"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.build_graph import build_graph  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="The question to ask")
    parser.add_argument(
        "--trace", action="store_true", help="Print the full state at each graph step"
    )
    args = parser.parse_args()

    app = build_graph()

    if args.trace:
        state = {"question": args.question}
        for step_output in app.stream(state):
            for node_name, node_state in step_output.items():
                print(f"\n=== after node: {node_name} ===")
                for k, v in node_state.items():
                    text = str(v)
                    print(f"  {k}: {text[:300]}{'...' if len(text) > 300 else ''}")
        return

    result = app.invoke({"question": args.question})
    print(result["final_answer"])


if __name__ == "__main__":
    main()
