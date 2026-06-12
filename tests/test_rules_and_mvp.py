from __future__ import annotations

from datetime import date

from crawler.eloboard import ELOBoardClient, MatchSummary, choose_daily_match, parse_match_detail
from cards.generator import generate_cards
from database.store import HistoryStore
from report.generator import WECHAT_TITLE_MAX_CHARS, choose_mvp, generate_article_locally, sanitize_article, GeneratedArticle
from report.html import compact_wechat_html, render_article_html
from translator.rules import load_translate_rules
from wechat.client import truncate_chars


def test_translate_rules_load_players_and_maps() -> None:
    rules = load_translate_rules()
    assert rules.translate_player("김민철") == "永康"
    assert rules.translate_player("민철") == "永康"
    assert rules.translate_map("매치") == "赛点"


def test_parse_saved_shape_and_mvp() -> None:
    html = """
    <html><head><title>2026.06.08 (월) 스타 5:5 메이저 프로리그</title></head>
    <body><article class="view-content">
    Z 김민철 김성대 P 변현제 T 이재호
    [민철팀] 김민철 김성대
    [현제팀] 변현제 이재호
    [1SET - 7/4 프로리그]
    1. [매치] 김민철Z (승) vs (패) 변현제P
    2. [실피] 김성대Z (패) vs (승) 이재호T
    민철팀 (승) 2 : 1 (패) 현제팀
    최종 결과 민철팀 1 : 0 승
    </article></body></html>
    """
    report = parse_match_detail(html, "https://example.com?wr_id=1", "1")
    assert report.team_a.display_name == "永康队"
    assert report.team_a.score == 1
    assert report.rounds[0].matches[0].winner_display == "永康"
    assert choose_mvp(report).display_name in {"永康", "光哥"}


def test_choose_daily_match_prefers_major_over_k_league() -> None:
    matches = [
        MatchSummary("2433", "2026.05.20 (수) 스타 5:5 K리그", "k", date(2026, 5, 20)),
        MatchSummary("2434", "2026.05.20 (수) 스타 5:5 메이저 프로리그", "m", date(2026, 5, 20)),
        MatchSummary("2432", "2026.05.19 (화) 스타 5:5 메이저 프로리그", "old", date(2026, 5, 19)),
    ]
    assert choose_daily_match(matches).match_id == "2434"


def test_choose_daily_match_uses_only_match_when_no_same_day_competition() -> None:
    matches = [
        MatchSummary("2433", "2026.05.20 (수) 스타 5:5 K리그", "k", date(2026, 5, 20)),
        MatchSummary("2432", "2026.05.19 (화) 스타 5:5 메이저 프로리그", "old", date(2026, 5, 19)),
    ]
    assert choose_daily_match(matches).match_id == "2433"


def test_latest_valid_report_skips_unparseable_latest_candidate(monkeypatch) -> None:
    matches = [
        MatchSummary("2454", "2026.06.11 (목) 스타 5:5 메이저 프로리그", "https://example.com/?wr_id=2454", date(2026, 6, 11)),
        MatchSummary("2453", "2026.06.11 (목) 스타 5:5 K리그", "https://example.com/?wr_id=2453", date(2026, 6, 11)),
    ]
    good_html = """
    <html><head><title>2026.06.11 (목) 스타 5:5 K리그</title></head>
    <body><article class="view-content">
    Z 김민철 P 김윤중
    [민철팀] 김민철
    [윤중팀] 김윤중
    [1SET - 7/4 프로리그]
    1. [매치] 김민철Z (승) vs (패) 김윤중P
    민철팀 (승) 1 : 0 (패) 윤중팀
    최종 결과 민철팀 1 : 0 승
    </article></body></html>
    """

    client = ELOBoardClient()
    monkeypatch.setattr(client, "list_matches", lambda limit=30: matches)
    monkeypatch.setattr(client, "fetch_html", lambda url: "<html><body>empty</body></html>" if "2454" in url else good_html)

    report = client.fetch_match()
    assert report.match_id == "2453"
    assert report.player_stats
    assert report.rounds[0].matches


def test_parse_unnumbered_super_ace_and_spaced_team_score() -> None:
    html = """
    <html><head><title>2026.06.09 (화) 스타 5:5 메이저 프로리그</title></head>
    <body><article class="view-content">
    Z 김정우 P 김윤중 T 정영재
    [영재팀] 정영재 김정우
    [병영팀] 김윤중
    [1SET - 7/4 프로리그]
    1. [제인] 정영재T (승) vs (패) 김윤중P
    영재팀 (승) 1 : 0 (패) 병영 팀
    [3SET - Super Ace Match]
    슈에 방식 룰렛: 자연빵
    [녹아] 정영재T (승) vs (패) 김윤중P
    최종 결과 영재팀 2 : 1 승
    </article></body></html>
    """
    report = parse_match_detail(html, "https://example.com?wr_id=2450", "2450")
    assert report.rounds[0].score_a == 1
    assert report.rounds[0].score_b == 0
    assert report.ace_round is not None
    assert len(report.ace_round.matches) == 1
    assert report.ace_round.matches[0].map_name == "击倒"
    assert report.ace_round.matches[0].winner_display == "橘右京"


def test_article_for_ace_match_cannot_say_no_ace() -> None:
    html = """
    <html><head><title>2026.06.09 (화) 스타 5:5 메이저 프로리그</title></head>
    <body><article class="view-content">
    Z 김정우 P 김윤중 T 정영재
    [영재팀] 정영재 김정우
    [병영팀] 김윤중
    [1SET - 7/4 프로리그]
    1. [제인] 정영재T (승) vs (패) 김윤중P
    영재팀 (승) 1 : 0 (패) 병영 팀
    [2SET - 9/5 위너스리그]
    1. [매치] 김정우Z (패) vs (승) 김윤중P
    영재팀 (패) 0 : 1 (승) 병영 팀
    [3SET - Super Ace Match]
    슈에 방식 룰렛: 자연빵
    [녹아] 정영재T (승) vs (패) 김윤중P
    최종 결과 영재팀 2 : 1 승
    </article></body></html>
    """
    report = parse_match_detail(html, "https://example.com?wr_id=2450", "2450")
    local = generate_article_locally(report)
    bad = GeneratedArticle(
        title=local.title,
        intro="本场没有大将战，最终比分为2:1。",
        round_reviews=[(round_item.name, "本轮未进行大将战，由前两轮赛果决定。") for round_item in report.all_rounds],
        mvp=local.mvp,
        mvp_text=local.mvp_text,
        summary="由于赛制未设置大将战，橘右京队以2:1获胜。",
        ai_generated=True,
    )

    checked = sanitize_article(report, bad, local)
    combined = "\n".join([checked.intro, checked.summary, *[text for _, text in checked.round_reviews]])
    assert "未进行大将战" not in combined
    assert "没有大将战" not in combined
    assert "击倒" in combined
    assert "大将战" in combined


def test_article_title_and_draft_title_stay_within_push_limit() -> None:
    html = """
    <html><head><title>2026.06.09 (화) 스타 5:5 메이저 프로리그</title></head>
    <body><article class="view-content">
    Z 김정우 P 김윤중 T 정영재
    [영재팀] 정영재 김정우
    [병영팀] 김윤중
    [1SET - 7/4 프로리그]
    1. [제인] 정영재T (승) vs (패) 김윤중P
    영재팀 (승) 1 : 0 (패) 병영 팀
    [3SET - Super Ace Match]
    [녹아] 정영재T (승) vs (패) 김윤중P
    최종 결과 영재팀 2 : 1 승
    </article></body></html>
    """
    report = parse_match_detail(html, "https://example.com?wr_id=2450", "2450")
    article = generate_article_locally(report)

    assert len(article.title) <= WECHAT_TITLE_MAX_CHARS
    long_title = "这是一条非常非常非常非常长的公众号推送标题用于测试截断规则"
    assert len(long_title) > WECHAT_TITLE_MAX_CHARS
    assert len(truncate_chars(long_title, WECHAT_TITLE_MAX_CHARS)) == WECHAT_TITLE_MAX_CHARS


def test_no_ace_match_omits_ace_card_and_article_block(tmp_path) -> None:
    html = """
    <html><head><title>2026.06.10 (수) 스타 5:5 메이저 프로리그</title></head>
    <body><article class="view-content">
    Z 김정우 김민철 P 김윤중
    [윤중팀] 김윤중
    [정우팀] 김정우 김민철
    [1SET - 7/4 프로리그]
    1. [제인] 김윤중P (패) vs (승) 김정우Z
    윤중팀 (패) 0 : 1 (승) 정우팀
    [2SET - 9/5 위너스리그]
    1. [매치] 김윤중P (패) vs (승) 김민철Z
    윤중팀 (패) 0 : 1 (승) 정우팀
    [3SET - Super Ace Match]
    슈에 방식 룰렛: 자연빵
    최종 결과 정우팀 2 : 0 승
    </article></body></html>
    """
    report = parse_match_detail(html, "https://example.com?wr_id=2451", "2451")
    assert report.ace_round is not None
    assert report.ace_round.matches == []

    article = generate_article_locally(report)
    card_paths = generate_cards(report, article.mvp, tmp_path / "cards")
    assert "ace" not in card_paths

    image_urls = {key: path.as_uri() for key, path in card_paths.items()}
    rendered = render_article_html(report, article, image_urls, tmp_path / "article.html")
    assert "大将战 - Super Ace Match" not in rendered
    assert "未进行" not in rendered
    assert "\n" not in rendered
    assert "padding:24px 12px 52px" not in rendered
    assert "display:none" not in rendered
    assert "font-size:16px;line-height:1.75" in rendered


def test_compact_wechat_html_removes_template_whitespace() -> None:
    html = """
    <section>
      <p>正文</p>
      <p>第二段</p>
    </section>
    """
    assert compact_wechat_html(html) == "<section><p>正文</p><p>第二段</p></section>"


def test_empty_media_id_does_not_count_as_published(tmp_path) -> None:
    store = HistoryStore(f"sqlite:///{tmp_path / 'agent.db'}")
    store.save_article("2451", "本地草稿已生成", "")
    assert not store.has_published_article("2451")

    store.save_article("2451", "公众号草稿已创建", "draft-media-id")
    assert store.has_published_article("2451")
