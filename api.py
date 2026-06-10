from __future__ import annotations

try:
    from fastapi import FastAPI
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("请先安装 FastAPI：pip install -r requirements.txt") from exc

from agent import StarCraftReportAgent
from database.store import HistoryStore


app = FastAPI(title="StarCraft Report Agent", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run(match_id: str | None = None, force: bool = False, publish: bool = False) -> dict[str, object]:
    result = StarCraftReportAgent().run(match_id, force=force, publish=publish)
    return {
        "match_id": result.report.match_id,
        "title": result.article.title,
        "score": result.report.score_text,
        "html_path": str(result.html_path),
        "draft_media_id": result.draft_media_id,
        "skipped": result.skipped,
    }


@app.get("/history")
def history(limit: int = 20) -> list[dict[str, object]]:
    return HistoryStore().latest_articles(limit)
