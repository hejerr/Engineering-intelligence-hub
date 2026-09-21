"""
Pluggable LLM client.

LLM_PROVIDER=mock (default): a deterministic, template-based "LLM" that
composes an answer directly from retrieved context. No API key, no cost,
no network call. This exists so the full LangGraph pipeline (routing,
retrieval, aggregation, self-grading, looping) is genuinely runnable and
demonstrable without anyone's API key -- including in review/CI.

LLM_PROVIDER=anthropic / openai: real LLM calls for production-quality
answers. Requires the corresponding API key as an environment variable.
"""
from __future__ import annotations

import re
from typing import List, Protocol

import config


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class MockLLMClient:
    """Deterministic, offline stand-in for a real LLM. Produces a readable,
    structured answer purely by summarizing/quoting the retrieved context
    that's handed to it -- enough to prove the graph plumbing works end to
    end without spending API credits."""

    def complete(self, system: str, user: str) -> str:
        # The graph nodes pass retrieved context inside the user prompt
        # between markers; pull it back out so the mock can "answer" from it.
        context_match = re.search(r"<context>(.*?)</context>", user, re.DOTALL)
        question_match = re.search(r"<question>(.*?)</question>", user, re.DOTALL)
        context = context_match.group(1).strip() if context_match else ""
        question = question_match.group(1).strip() if question_match else user.strip()

        if "GRADE_ANSWER_TASK" in system:
            # The grading node asks for a confidence score. The mock derives
            # it from the actual top retrieval similarity score (passed in
            # as TOP_SCORE) rather than just checking context length, so a
            # genuinely irrelevant question still triggers the retry loop.
            top_score_match = re.search(r"TOP_SCORE:\s*([0-9]*\.?[0-9]+)", user)
            top_score = float(top_score_match.group(1)) if top_score_match else 0.0
            # TF-IDF cosine similarities for real matches are typically
            # ~0.15-0.6; map that range onto a 0-1 confidence band.
            confidence = max(0.0, min(1.0, top_score * 1.8))
            return f"CONFIDENCE: {confidence:.2f}\nREASON: mock heuristic based on top retrieval similarity score ({top_score:.3f})."

        if "CLASSIFY_TASK" in system:
            return _mock_classify(question)

        if not context:
            return (
                "I couldn't find relevant material in the knowledge base for "
                f"this question ({question[:120]!r}). Try rephrasing, or check "
                "that the index was built (`python scripts/ingest.py`)."
            )

        snippets = [s.strip() for s in context.split("---") if s.strip()]
        bullet_points = "\n".join(f"- {s[:280].strip()}{'...' if len(s) > 280 else ''}" for s in snippets[:5])
        return (
            f"[MOCK LLM — set LLM_PROVIDER=anthropic or openai for a real answer]\n\n"
            f"Based on the retrieved material, here is what's relevant to:\n"
            f'"{question}"\n\n{bullet_points}\n\n'
            f"(This is a template composition of the retrieved chunks, not a "
            f"real generated answer -- see README.md to enable a real LLM.)"
        )


def _mock_classify(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["error", "bug", "fail", "crash", "incident", "broke", "issue", "not working", "404", "500", "422"]):
        return "incident"
    if any(w in q for w in ["architecture", "design", "how does", "diagram", "flow", "lifecycle", "internals"]):
        return "architecture"
    if any(w in q for w in ["function", "class", "def ", "implement", "source", "code", "signature"]):
        return "code"
    if any(w in q for w in ["how do i", "how to", "tutorial", "docs", "documentation", "guide", "example"]):
        return "docs"
    return "general"


class GeminiLLMClient:
    """Google Gemini via the unified `google-genai` SDK. Uses Google AI
    Studio's free tier -- no billing account required. Requires
    GEMINI_API_KEY (get one free at https://aistudio.google.com/apikey)."""

    def __init__(self, model: str | None = None):
        from google import genai

        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and put it in your .env file."
            )
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = model or config.GEMINI_MODEL

    def complete(self, system: str, user: str) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=config.LLM_TEMPERATURE,
            ),
        )
        return response.text or ""


class AnthropicLLMClient:
    def __init__(self, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or config.ANTHROPIC_MODEL

    def complete(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=config.LLM_TEMPERATURE,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class OpenAILLMClient:
    def __init__(self, model: str | None = None):
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model or config.OPENAI_MODEL

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=config.LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def get_llm_client(provider: str | None = None) -> LLMClient:
    provider = provider or config.LLM_PROVIDER
    if provider == "mock":
        return MockLLMClient()
    if provider == "gemini":
        return GeminiLLMClient()
    if provider == "anthropic":
        return AnthropicLLMClient()
    if provider == "openai":
        return OpenAILLMClient()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
