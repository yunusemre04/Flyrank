"""Settings come from environment variables only (see .env.example). Never hard-code keys."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _e(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    database_url: str
    provider: str  # gemini | ollama | mock
    gemini_api_key: str
    gemini_vision_model: str
    gemini_embed_model: str
    ollama_host: str
    ollama_vision_model: str
    ollama_embed_model: str
    image_dir: str
    posts_path: str
    eval_path: str
    taxonomy_path: str
    confidence_min: float  # below this an image is flagged, never auto-suggested
    similarity_threshold: float  # cosine cut-off, tune with `python -m scripts.eval --sweep`
    unknown_subject_margin: float  # extra strictness when the post's subject is not in the taxonomy
    top_k: int
    max_attempts: int
    retry_base_delay: float
    request_delay: float  # pause between items; raise it to respect free-tier rate limits
    budget_usd: float
    auto_migrate: bool


def get_settings() -> Settings:
    return Settings(
        database_url=_e("DATABASE_URL", f"sqlite:///{ROOT / 'app.db'}"),
        provider=_e("PROVIDER", "gemini").lower(),
        gemini_api_key=_e("GEMINI_API_KEY", ""),
        gemini_vision_model=_e("GEMINI_VISION_MODEL", "gemini-2.5-flash"),
        gemini_embed_model=_e("GEMINI_EMBED_MODEL", "gemini-embedding-001"),
        ollama_host=_e("OLLAMA_HOST", "http://localhost:11434"),
        ollama_vision_model=_e("OLLAMA_VISION_MODEL", "llava"),
        ollama_embed_model=_e("OLLAMA_EMBED_MODEL", "all-minilm"),
        image_dir=_e("IMAGE_DIR", str(ROOT / "data" / "images")),
        posts_path=_e("POSTS_PATH", str(ROOT / "data" / "posts.json")),
        eval_path=_e("EVAL_PATH", str(ROOT / "data" / "eval.json")),
        taxonomy_path=_e("TAXONOMY_PATH", str(ROOT / "data" / "taxonomy.json")),
        confidence_min=float(_e("CONFIDENCE_MIN", "0.6")),
        similarity_threshold=float(_e("SIMILARITY_THRESHOLD", "0.6")),
        unknown_subject_margin=float(_e("UNKNOWN_SUBJECT_MARGIN", "0.05")),
        top_k=int(_e("TOP_K", "5")),
        max_attempts=int(_e("MAX_ATTEMPTS", "3")),
        retry_base_delay=float(_e("RETRY_BASE_DELAY", "2")),
        request_delay=float(_e("REQUEST_DELAY", "0")),
        budget_usd=float(_e("BUDGET_USD", "1.0")),
        auto_migrate=_e("AUTO_MIGRATE", "true").lower() == "true",
    )
