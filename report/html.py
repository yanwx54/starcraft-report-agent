from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import ROOT_DIR, settings
from models import BattleReport
from report.generator import GeneratedArticle


def render_article_html(
    report: BattleReport,
    article: GeneratedArticle,
    image_urls: dict[str, str],
    out_path: Path | None = None,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(ROOT_DIR / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("article.html.j2")
    round_blocks = []
    for round_index, (round_item, review) in enumerate(zip(report.all_rounds, article.round_reviews), start=1):
        key = "ace" if "大将战" in round_item.name or "Super Ace" in round_item.name else f"round_{round_index}"
        if key == "ace" and not round_item.matches:
            continue
        images = [image_urls[key]] if key in image_urls else []
        round_blocks.append({"name": review[0], "text": review[1], "images": images})
    html = compact_wechat_html(template.render(report=report, article=article, images=image_urls, round_blocks=round_blocks))
    if out_path is None:
        out_path = settings.article_dir / f"{report.match_id}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return html


def compact_wechat_html(html: str) -> str:
    """Keep WeChat drafts from amplifying template whitespace into visible gaps."""
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r"\s*\n\s*", "", html)
    return html.strip()
