import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _int_env(name: str, default: int | None) -> int | None:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    help_center_url: str
    locale: str
    store_display_name: str
    articles_dir: Path
    report_path: Path
    max_articles: int | None
    max_tokens_per_chunk: int
    max_overlap_tokens: int
    upload_workers: int
    model: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            # The brief runs the image with `-e API_KEY=...`, so accept that alongside the Gemini names.
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY"),
            help_center_url=os.getenv("HELP_CENTER_URL", "https://support.optisigns.com").rstrip("/"),
            locale=os.getenv("HELP_CENTER_LOCALE", "en-us"),
            store_display_name=os.getenv("STORE_DISPLAY_NAME", "optibot-kb"),
            articles_dir=Path(os.getenv("ARTICLES_DIR", "articles")),
            report_path=Path(os.getenv("REPORT_PATH", "runs/last_run.json")),
            max_articles=_int_env("MAX_ARTICLES", None),
            max_tokens_per_chunk=_int_env("CHUNK_MAX_TOKENS", 400),
            max_overlap_tokens=_int_env("CHUNK_OVERLAP_TOKENS", 60),
            upload_workers=_int_env("UPLOAD_WORKERS", 4),
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        )
