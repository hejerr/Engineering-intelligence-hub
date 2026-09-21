#!/usr/bin/env python3
"""
Ablation study: does the confidence-driven retry loop actually help?

Runs the same set of test questions through the graph twice:
  - "no_retry":   max_iterations forced to 0 (single retrieval attempt,
                  whatever the initial classification routed to)
  - "with_retry": normal MAX_GRAPH_ITERATIONS from config/.env (the loop is
                  free to widen the search and try again on low confidence)

For each question it records the classified query_type, confidence score,
iterations actually used, and number of sources retrieved -- then prints a
per-question delta table plus summary stats, and saves raw results to JSON.

This is exactly the kind of evidence a "we added a retry loop" claim needs:
without it, you don't actually know whether the loop is pulling its weight.

Usage:
    python scripts/eval_retry_loop.py
    python scripts/eval_retry_loop.py --questions my_questions.json
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from src.graph.build_graph import build_graph  # noqa: E402

# A deliberately mixed set: some questions should classify cleanly (code,
# docs, architecture, incidents), and a few are intentionally vague or
# off-topic, since that's where a retry loop should earn its keep.
DEFAULT_QUESTIONS = [
    "What does the Depends() function actually do under the hood?",
    "How does FastAPI serialize the return value of a path operation?",
    "Where is APIRoute defined and what does it store?",
    "How do I add a custom header to every response?",
    "How can I upload a file in a FastAPI endpoint?",
    "How do I set a default value for a query parameter?",
    "How does a request flow through FastAPI from start to finish?",
    "Explain how FastAPI's dependency injection resolves sub-dependencies.",
    "What happens when a mounted sub-application receives a request?",
    "Why would background tasks lose headers when combined with streaming responses?",
    "What was the bug with BasicAuth realm handling?",
    "Why did APIRoute.tags become invisible to type checkers?",
    "How do I get started understanding this codebase?",
    "What should a new engineer read first?",
    "Tell me about error handling in this project.",
    "What's the best pizza topping combination?",  # deliberately irrelevant
]


def run_condition(app, questions, max_iterations, label):
    results = []
    for q in questions:
        initial_state = {"question": q}
        if max_iterations is not None:
            initial_state["max_iterations"] = max_iterations
        start = time.time()
        result = app.invoke(initial_state)
        elapsed = time.time() - start
        confidence = result.get("confidence", 0.0)
        iterations_used = result.get("iteration", 0) + 1
        results.append(
            {
                "question": q,
                "query_type": result.get("query_type"),
                "confidence": confidence,
                "iterations_used": iterations_used,
                "num_sources": len(result.get("sources", [])),
                "answer_chars": len(result.get("draft_answer", "")),
                "elapsed_s": round(elapsed, 2),
            }
        )
        print(f"  [{label}] {q[:55]:57s} confidence={confidence:.2f} iters={iterations_used}")
    return results


def summarize(results, label):
    confidences = [r["confidence"] for r in results]
    iterations = [r["iterations_used"] for r in results]
    print(f"\n=== {label} ===")
    print(f"  mean confidence: {statistics.mean(confidences):.3f}")
    print(f"  min confidence:  {min(confidences):.3f}")
    print(f"  mean iterations: {statistics.mean(iterations):.2f}")
    below = sum(1 for c in confidences if c < config.CONFIDENCE_THRESHOLD)
    print(f"  questions below threshold ({config.CONFIDENCE_THRESHOLD}): {below}/{len(confidences)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=None, help="JSON file: a list of question strings")
    parser.add_argument(
        "--out",
        type=Path,
        default=config.DATA_PROCESSED_DIR / "eval_retry_loop.json",
    )
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text()) if args.questions else DEFAULT_QUESTIONS

    app = build_graph()

    print(f"Running {len(questions)} questions WITHOUT retry (max_iterations=0)...")
    no_retry_results = run_condition(app, questions, max_iterations=0, label="no_retry ")

    print(f"\nRunning {len(questions)} questions WITH retry (max_iterations={config.MAX_GRAPH_ITERATIONS})...")
    with_retry_results = run_condition(app, questions, max_iterations=None, label="w/_retry")

    summarize(no_retry_results, "NO RETRY (baseline)")
    summarize(with_retry_results, "WITH RETRY")

    print("\n=== Per-question confidence delta (with_retry - no_retry) ===")
    improved = 0
    for a, b in zip(no_retry_results, with_retry_results):
        delta = b["confidence"] - a["confidence"]
        flag = ""
        if delta > 0.01:
            flag = "  <-- improved by retry"
            improved += 1
        elif delta < -0.01:
            flag = "  <-- WORSE with retry (investigate)"
        print(f"  {a['question'][:55]:57s} {a['confidence']:.2f} -> {b['confidence']:.2f} ({delta:+.2f}){flag}")

    print(f"\n{improved}/{len(questions)} questions improved by the retry loop.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"no_retry": no_retry_results, "with_retry": with_retry_results}, indent=2)
    )
    print(f"\nRaw results saved to {args.out}")


if __name__ == "__main__":
    main()
