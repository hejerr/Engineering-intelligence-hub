"""
Central configuration for the Engineering Intelligence Hub.

Every setting can be overridden with an environment variable (see
`.env.example`). Defaults are chosen so the project runs out of the box
with zero API keys and zero external downloads:

  - EMBEDDING_PROVIDER=tfidf  -> local, deterministic, scikit-learn based,
    no model download required.
  - LLM_PROVIDER=mock         -> a template-based "LLM" that composes an
    answer directly from retrieved context, so you can see the full
    LangGraph pipeline run end-to-end for free before wiring up a real key.

To use real embeddings / a real LLM, set the env vars described below.
"""
import os
from pathlib import Path

# Load .env if python-dotenv is available (optional dependency)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
VECTOR_STORE_DIR = DATA_PROCESSED_DIR / "vector_store"

# --- Corpora -----------------------------------------------------------
# Each corpus becomes its own retrievable collection, so the LangGraph
# router can send a query to exactly the source types it needs.
CORPORA = {
    "code": DATA_RAW_DIR / "code",
    "docs": DATA_RAW_DIR / "docs",
    "architecture": DATA_RAW_DIR / "architecture",
    "incidents": DATA_RAW_DIR / "incidents",
}

# --- Chunking ------------------------------------------------------------
CODE_CHUNK_MAX_LINES = int(os.getenv("CODE_CHUNK_MAX_LINES", "80"))
CODE_CHUNK_OVERLAP_LINES = int(os.getenv("CODE_CHUNK_OVERLAP_LINES", "10"))
TEXT_CHUNK_MAX_CHARS = int(os.getenv("TEXT_CHUNK_MAX_CHARS", "1800"))
TEXT_CHUNK_OVERLAP_CHARS = int(os.getenv("TEXT_CHUNK_OVERLAP_CHARS", "200"))

# --- Embeddings ----------------------------------------------------------
# "tfidf"       -> scikit-learn TF-IDF, local only, no downloads (default)
# "huggingface" -> sentence-transformers local dense embeddings (needs
#                  internet access to huggingface.co on first run)
# "openai"      -> OpenAI embeddings API (needs OPENAI_API_KEY)
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "tfidf")
HUGGINGFACE_EMBEDDING_MODEL = os.getenv(
    "HUGGINGFACE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# --- LLM -------------------------------------------------------------------
# "mock"      -> free, offline, template-based synthesis (default)
# "gemini"    -> Google Gemini via GEMINI_API_KEY (free tier, no billing needed)
# "anthropic" -> Claude via ANTHROPIC_API_KEY
# "openai"    -> GPT via OPENAI_API_KEY
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Gemini model names change fairly often -- if this default ever 404s, check
# https://aistudio.google.com/ (the "Rate Limits" / models page there always
# shows current, free-tier-eligible model names) and override with GEMINI_MODEL.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# --- Retrieval -------------------------------------------------------------
TOP_K_PER_SOURCE = int(os.getenv("TOP_K_PER_SOURCE", "4"))
MAX_GRAPH_ITERATIONS = int(os.getenv("MAX_GRAPH_ITERATIONS", "2"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # optional, raises API rate limits
