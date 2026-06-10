from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cards.generator import generate_cards
from config.settings import ensure_output_dirs, settings
from crawler.eloboard import ELOBoardClient
from database.store import HistoryStore
from models import BattleReport
from notify.pushplus import PushPlusClient
from report.generator import GeneratedArticle, generate_article
from report.html import render_article_html
from wechat.client import WechatClient, local_image_urls


@dataclass(slots=True)
class RunResult:
    report: BattleReport
    article: GeneratedArticle
    html_path: Path
    card_paths: dict[str, Path]
    draft_media_id: str
    skipped: bool = False


class StarCraftReportAgent:
    def __init__(self) -> None:
        ensure_output_dirs()
        self.crawler = ELOBoardClient()
        self.store = HistoryStore()
        self.wechat = WechatClient()
        self.notify = PushPlusClient()

    def run(self, match_id_or_url: str | None = None, force: bool = False, publish: bool = False) -> RunResult:
        report = self.crawler.fetch_match(match_id_or_url)
        if self.store.has_match(report.match_id) and not force:
            article = generate_article(report)
            html_path = settings.article_dir / f"{report.match_id}.html"
            return RunResult(report, article, html_path, {}, "", skipped=True)

        article = generate_article(report)
        card_paths = generate_cards(report, article.mvp)

        image_urls = local_image_urls(card_paths)
        draft_media_id = ""
        html_path = settings.article_dir / f"{report.match_id}.html"
        html = render_article_html(report, article, image_urls, html_path)

        should_publish = publish and self.wechat.enabled and not settings.dry_run
        if should_publish:
            token = self.wechat.access_token()
            image_urls = {key: self.wechat.upload_image(path, token) for key, path in card_paths.items()}
            html = render_article_html(report, article, image_urls, html_path)
            thumb_path = card_paths.get("hero") or next(iter(card_paths.values()))
            thumb_media_id = self.wechat.upload_thumb(thumb_path, token)
            draft_media_id = self.wechat.add_draft(article.title, html, token, thumb_media_id)

        self.store.save_match(report)
        self.store.save_article(report.match_id, article.title, draft_media_id)
        self.notify.send(report, "已创建" if draft_media_id else "本地草稿已生成")

        return RunResult(report, article, html_path, card_paths, draft_media_id)
