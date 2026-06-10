from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, MetaData, String, Table, Text, create_engine, select
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.dialects.sqlite import INTEGER as SQLITE_INTEGER
from sqlalchemy.schema import Column

from config.settings import settings
from models import BattleReport


metadata = MetaData()

id_type = MYSQL_BIGINT().with_variant(SQLITE_INTEGER(), "sqlite")

article_history = Table(
    "article_history",
    metadata,
    Column("id", id_type, primary_key=True, autoincrement=True),
    Column("match_id", String(50), unique=True, nullable=False),
    Column("title", String(255), nullable=False),
    Column("media_id", String(255), default=""),
    Column("created_at", DateTime, nullable=False),
)

match_history = Table(
    "match_history",
    metadata,
    Column("id", id_type, primary_key=True, autoincrement=True),
    Column("match_id", String(50), unique=True, nullable=False),
    Column("match_date", Date),
    Column("team_a", String(100), nullable=False),
    Column("team_b", String(100), nullable=False),
    Column("score", String(20), nullable=False),
    Column("raw_json", JSON().with_variant(Text(), "sqlite"), nullable=False),
)


class HistoryStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url, future=True)
        metadata.create_all(self.engine)

    def has_match(self, match_id: str) -> bool:
        stmt = select(match_history.c.id).where(match_history.c.match_id == match_id).limit(1)
        with self.engine.connect() as conn:
            return conn.execute(stmt).first() is not None

    def save_match(self, report: BattleReport) -> None:
        raw_payload: Any = report.to_dict()
        if self.engine.dialect.name == "sqlite":
            raw_payload = json.dumps(raw_payload, ensure_ascii=False, default=str)

        values = {
            "match_id": report.match_id,
            "match_date": report.match_date,
            "team_a": report.team_a.display_name,
            "team_b": report.team_b.display_name,
            "score": report.score_text,
            "raw_json": raw_payload,
        }
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(match_history.c.id).where(match_history.c.match_id == report.match_id)
            ).scalar_one_or_none()
            if existing:
                conn.execute(match_history.update().where(match_history.c.id == existing).values(**values))
            else:
                conn.execute(match_history.insert().values(**values))

    def save_article(self, match_id: str, title: str, media_id: str = "") -> None:
        values = {
            "match_id": match_id,
            "title": title,
            "media_id": media_id,
            "created_at": datetime.now(),
        }
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(article_history.c.id).where(article_history.c.match_id == match_id)
            ).scalar_one_or_none()
            if existing:
                conn.execute(article_history.update().where(article_history.c.id == existing).values(**values))
            else:
                conn.execute(article_history.insert().values(**values))

    def latest_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        stmt = select(article_history).order_by(article_history.c.created_at.desc()).limit(limit)
        with self.engine.connect() as conn:
            return [dict(row._mapping) for row in conn.execute(stmt)]
