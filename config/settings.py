from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# Load local secret files without overriding real environment variables.
# Priority: OS environment > .env.local > .env.
_load_dotenv(ROOT_DIR / ".env.local")
_load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT_DIR
    output_dir: Path = ROOT_DIR / "output"
    card_dir: Path = ROOT_DIR / "output" / "cards"
    article_dir: Path = ROOT_DIR / "output" / "articles"
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'output' / 'agent.db'}")
    eloboard_list_url: str = os.getenv(
        "ELOBOARD_LIST_URL",
        "https://eloboard.com/men/bbs/board.php?bo_table=pro_league",
    )
    eloboard_http_proxy: str = os.getenv("ELOBOARD_HTTP_PROXY", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    wechat_app_id: str = os.getenv("WECHAT_APP_ID", "")
    wechat_app_secret: str = os.getenv("WECHAT_APP_SECRET", "")
    pushplus_token: str = os.getenv("PUSHPLUS_TOKEN", "")
    dry_run: bool = os.getenv("DRY_RUN", "1").lower() not in {"0", "false", "no"}


settings = Settings()


def ensure_output_dirs() -> None:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.card_dir.mkdir(parents=True, exist_ok=True)
    settings.article_dir.mkdir(parents=True, exist_ok=True)
