from __future__ import annotations

import json
import re
from dataclasses import dataclass

from models import BattleReport, PlayerStat, Round
from translator.deepseek import DeepSeekTranslator


WECHAT_TITLE_MAX_CHARS = 25


@dataclass
class GeneratedArticle:
    title: str
    intro: str
    round_reviews: list[tuple[str, str]]
    mvp: PlayerStat
    mvp_text: str
    summary: str
    ai_generated: bool = False


def choose_mvp(report: BattleReport) -> PlayerStat:
    if not report.player_stats:
        raise ValueError("没有可评选 MVP 的选手统计")
    return sorted(
        report.player_stats,
        key=lambda p: (p.max_streak, p.closing_win, p.win_rate, p.wins, -p.losses),
        reverse=True,
    )[0]


def generate_article(report: BattleReport, use_ai: bool = True) -> GeneratedArticle:
    if use_ai:
        ai_article = generate_article_with_deepseek(report)
        if ai_article:
            return ai_article
    return generate_article_locally(report)


def generate_article_with_deepseek(report: BattleReport) -> GeneratedArticle | None:
    client = DeepSeekTranslator()
    if not client.enabled:
        return None

    mvp = choose_mvp(report)
    local = generate_article_locally(report)
    payload = build_article_payload(report, mvp)
    system = (
        "你是微信公众号星际争霸团战战报作者。只基于结构化赛果写作；"
        "因为没有比赛过程录像，不要编造战术细节、操作过程、心理活动或不存在的剧情。"
        "风格适合公众号发布：有节奏、有梗但不过度口水，重点突出比分走势、连胜和收官局。"
        "地图名必须使用输入中的中文翻译名，选手名和队名使用输入中的显示名。"
        "如果结构化赛果中 has_ace_match 为 true，必须写大将战，严禁写未进行大将战、无需大将战或由前两轮决定。"
        "如果 has_ace_match 为 false，才可以写未进行大将战。"
        "必须返回严格 JSON，不要 Markdown，不要代码块。"
    )
    user = (
        "请生成一篇韩国星际争霸团战公众号战报草稿。JSON 字段必须包含："
        "title、intro、round_reviews、mvp_text、summary。"
        f"title 必须适合公众号推送，最多 {WECHAT_TITLE_MAX_CHARS} 个字符。"
        "round_reviews 是数组，长度必须与 rounds 一致，每项包含 name 和 text。"
        "intro 约100字，summary 约180-240字，round text 只描述赛果和比分走势。"
        "所有比分、胜方、地图、选手、是否有大将战必须与结构化赛果完全一致。"
        f"\n\n结构化赛果：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    try:
        raw = client.chat(system=system, user=user, temperature=0.75)
        data = parse_json_object(raw)
        round_reviews = []
        review_items = data.get("round_reviews", [])
        for index, round_item in enumerate(report.all_rounds):
            if isinstance(review_items, list) and index < len(review_items) and isinstance(review_items[index], dict):
                item = review_items[index]
                round_reviews.append(
                    (
                        decode_literal_unicode(str(item.get("name") or round_item.name)),
                        decode_literal_unicode(str(item.get("text") or "")),
                    )
                )
            else:
                round_reviews.append((round_item.name, describe_round(report, round_item)))
        article = GeneratedArticle(
            title=decode_literal_unicode(str(data.get("title") or local.title)),
            intro=decode_literal_unicode(str(data.get("intro") or local.intro)),
            round_reviews=round_reviews,
            mvp=mvp,
            mvp_text=decode_literal_unicode(str(data.get("mvp_text") or local.mvp_text)),
            summary=decode_literal_unicode(str(data.get("summary") or local.summary)),
            ai_generated=True,
        )
        return sanitize_article(report, article, local)
    except Exception:
        return None


def generate_article_locally(report: BattleReport) -> GeneratedArticle:
    mvp = choose_mvp(report)
    score = f"{report.team_a.display_name} {report.score_text} {report.team_b.display_name}"
    title = build_short_title(report, mvp)

    intro = build_intro(report, mvp)

    round_reviews = [(round_item.name, describe_round(report, round_item)) for round_item in report.all_rounds]
    if not round_reviews:
        round_reviews = [("比赛结果", f"本场最终结果为 {score}。页面未解析到逐局对阵，建议人工复核原始链接。")]

    mvp_text = (
        f"{mvp.display_name}本场打出{mvp.wins}胜{mvp.losses}负，最长{mvp.max_streak}连胜。"
        "按“连胜次数优先、终结比赛其次、胜率兜底”的规则，他是本场 MVP。"
    )

    summary = build_summary(report, mvp)

    return GeneratedArticle(
        title=title,
        intro=intro,
        round_reviews=round_reviews,
        mvp=mvp,
        mvp_text=mvp_text,
        summary=summary,
    )


def build_article_payload(report: BattleReport, mvp: PlayerStat) -> dict[str, object]:
    ace_match = report.ace_round.matches[0] if report.ace_round and report.ace_round.matches else None
    return {
        "match_id": report.match_id,
        "date": report.match_date.isoformat() if report.match_date else "",
        "league": report.league_name,
        "score": f"{report.team_a.display_name} {report.score_text} {report.team_b.display_name}",
        "has_ace_match": bool(ace_match),
        "ace_match": {
            "map": ace_match.map_name,
            "player_a": f"{ace_match.player_a.display_name}({ace_match.player_a.race})",
            "player_b": f"{ace_match.player_b.display_name}({ace_match.player_b.race})",
            "winner": ace_match.winner_display,
            "winner_team": report.ace_round.winner_team if report.ace_round else "",
        }
        if ace_match
        else None,
        "teams": {
            "team_a": {
                "name": report.team_a.display_name,
                "score": report.team_a.score,
                "players": [f"{p.display_name}({p.race})" for p in report.team_a.players],
            },
            "team_b": {
                "name": report.team_b.display_name,
                "score": report.team_b.score,
                "players": [f"{p.display_name}({p.race})" for p in report.team_b.players],
            },
        },
        "rounds": [
            {
                "name": round_item.name,
                "score": f"{round_item.score_a}:{round_item.score_b}",
                "winner_team": round_item.winner_team,
                "matches": [
                    {
                        "game": game.id,
                        "map": game.map_name,
                        "player_a": f"{game.player_a.display_name}({game.player_a.race})",
                        "player_b": f"{game.player_b.display_name}({game.player_b.race})",
                        "winner": game.winner_display,
                    }
                    for game in round_item.matches
                ],
            }
            for round_item in report.all_rounds
        ],
        "mvp": {
            "name": mvp.display_name,
            "race": mvp.race,
            "wins": mvp.wins,
            "losses": mvp.losses,
            "max_streak": mvp.max_streak,
            "closing_win": mvp.closing_win,
        },
    }


def parse_json_object(raw: str) -> dict[str, object]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, flags=re.S)
    if not match:
        raise ValueError("DeepSeek 未返回 JSON 对象")
    return json.loads(match.group(0))


def decode_literal_unicode(value: str) -> str:
    """Decode strings that contain literal '\\u4e2d' sequences from model output."""
    if "\\u" not in value:
        return value

    def replace(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return re.sub(r"\\u([0-9a-fA-F]{4})", replace, value)


def describe_round(report: BattleReport, round_item: Round) -> str:
    if is_ace_round(round_item):
        return describe_ace_round(report, round_item)

    if not round_item.matches:
        return "本轮没有实际对局记录，页面显示为 Super Ace 规则说明或未进行大将战。"

    lead = f"{round_item.name}，{report.team_a.display_name} {round_item.score_a}:{round_item.score_b} {report.team_b.display_name}。"
    winners = [game.winner_display for game in round_item.matches]
    streak_player, streak = _round_streak(round_item)
    highlights: list[str] = []
    if winners:
        highlights.append(f"本轮胜场来自：{'、'.join(winners)}。")
    if streak_player and streak >= 2:
        highlights.append(f"{streak_player}在这一轮打出{streak}连胜，是比分拉开的关键。")
    closing = round_item.matches[-1]
    opponent = closing.player_b.display_name if closing.winner == closing.player_a.raw_name else closing.player_a.display_name
    highlights.append(f"收官局在 {closing.map_name} 展开，{closing.winner_display}击败{opponent}，为本轮结果收尾。")
    return lead + "".join(highlights)


def sanitize_article(report: BattleReport, article: GeneratedArticle, fallback: GeneratedArticle) -> GeneratedArticle:
    round_reviews: list[tuple[str, str]] = []
    provided = article.round_reviews or []
    for index, round_item in enumerate(report.all_rounds):
        text = ""
        if index < len(provided):
            text = provided[index][1].strip()
        if not text or has_fact_conflict(report, text) or is_ace_round(round_item):
            text = describe_round(report, round_item)
        round_reviews.append((round_item.name, text))

    title = article.title.strip() or fallback.title
    intro = article.intro.strip() or fallback.intro
    summary = article.summary.strip() or fallback.summary
    mvp_text = article.mvp_text.strip() or fallback.mvp_text

    if has_fact_conflict(report, title):
        title = fallback.title
    if len(title) > WECHAT_TITLE_MAX_CHARS:
        title = build_short_title(report, article.mvp)
    if has_fact_conflict(report, intro) or misses_required_ace(report, intro):
        intro = fallback.intro
    if has_fact_conflict(report, summary) or misses_required_ace(report, summary):
        summary = fallback.summary
    if has_fact_conflict(report, mvp_text):
        mvp_text = fallback.mvp_text

    return GeneratedArticle(
        title=title,
        intro=intro,
        round_reviews=round_reviews,
        mvp=article.mvp,
        mvp_text=mvp_text,
        summary=summary,
        ai_generated=article.ai_generated,
    )


def has_fact_conflict(report: BattleReport, text: str) -> bool:
    if report.ace_round and report.ace_round.matches:
        no_ace_phrases = (
            "未进行大将战",
            "没有大将战",
            "无需大将战",
            "不需要大将战",
            "未进入大将战",
            "未打大将战",
            "由前两轮赛果决定",
            "由前两轮结果决定",
        )
        return any(phrase in text for phrase in no_ace_phrases)
    return False


def build_short_title(report: BattleReport, mvp: PlayerStat) -> str:
    winner = report.winner_team.display_name
    loser = report.loser_team.display_name
    score = f"{report.winner_team.score}:{report.loser_team.score}"
    if report.ace_round and report.ace_round.matches:
        title = f"{winner}{score}险胜{loser}，大将战定胜"
    elif mvp.max_streak >= 3:
        title = f"{winner}{score}击败{loser}，{mvp.display_name}{mvp.max_streak}连胜"
    else:
        title = f"{winner}{score}击败{loser}"
    return title[:WECHAT_TITLE_MAX_CHARS]


def misses_required_ace(report: BattleReport, text: str) -> bool:
    return bool(report.ace_round and report.ace_round.matches and "大将" not in text and "Super Ace" not in text)


def is_ace_round(round_item: Round) -> bool:
    return "大将战" in round_item.name or "Super Ace" in round_item.name


def describe_ace_round(report: BattleReport, round_item: Round) -> str:
    if not round_item.matches:
        return "前两轮已经决出总比分，本场没有进入大将战。"

    game = round_item.matches[-1]
    winner_player = game.player_a if game.winner == game.player_a.raw_name else game.player_b
    loser_player = game.player_b if game.winner == game.player_a.raw_name else game.player_a
    winner_team = round_item.winner_team or team_name_for_player(report, winner_player.raw_name) or report.winner_team.display_name
    return (
        f"大将战一局定胜负，{winner_player.display_name}({winner_player.race})在{game.map_name}地图上"
        f"击败{loser_player.display_name}({loser_player.race})，帮助{winner_team}拿下决胜局，"
        f"最终总比分定格为{report.team_a.display_name} {report.score_text} {report.team_b.display_name}。"
    )


def describe_ace_result(report: BattleReport) -> str:
    if not report.ace_round or not report.ace_round.matches:
        return ""
    return describe_ace_round(report, report.ace_round)


def build_intro(report: BattleReport, mvp: PlayerStat) -> str:
    winner = report.winner_team.display_name
    loser = report.loser_team.display_name
    date_text = format_date(report)
    if report.ace_round and report.ace_round.matches:
        ace = report.ace_round.matches[-1]
        return (
            f"{date_text}，{report.league_name}战罢。{winner}与{loser}前两轮战成1:1，"
            f"比赛被拖入大将战。决胜局中，{ace.winner_display}在{ace.map_name}地图完成收官，"
            f"帮助{winner}以总比分{report.winner_team.score}:{report.loser_team.score}险胜。"
            f"{mvp.display_name}本场打出{mvp.wins}胜{mvp.losses}负，仍是全场最亮眼的数据点之一。"
        )
    return (
        f"{date_text}，{report.league_name}战罢。{winner}与{loser}完成前两轮较量，"
        f"{winner}以总比分{report.winner_team.score}:{report.loser_team.score}收下胜利。"
        f"{mvp.display_name}凭借{mvp.wins}胜{mvp.losses}负和最长{mvp.max_streak}连胜成为比赛焦点。"
    )


def build_summary(report: BattleReport, mvp: PlayerStat) -> str:
    winner = report.winner_team.display_name
    loser = report.loser_team.display_name
    parts: list[str] = []
    for round_item in report.rounds:
        parts.append(f"{round_item.name}由{round_item.winner_team or '胜方'}以{round_item.score_a}:{round_item.score_b}拿下")
    base = "；".join(parts)
    if report.ace_round and report.ace_round.matches:
        ace = report.ace_round.matches[-1]
        return (
            f"本场走势非常清晰：{base}，前两轮过后双方战成1:1。"
            f"真正的胜负手出现在大将战，{ace.winner_display}在{ace.map_name}地图击败对手，"
            f"为{winner}锁定{report.winner_team.score}:{report.loser_team.score}的总比分。"
            f"{mvp.display_name}虽然凭借{mvp.wins}胜{mvp.losses}负和最长{mvp.max_streak}连胜打出存在感，"
            f"但{winner}在决胜局的收官更稳，最终笑到最后。"
        )
    return (
        f"本场走势非常清晰：{base}，{winner}最终以{report.winner_team.score}:{report.loser_team.score}击败{loser}。"
        f"{mvp.display_name}凭借{mvp.wins}胜{mvp.losses}负和最长{mvp.max_streak}连胜成为场上焦点，"
        f"{loser}虽有单点回应，但没能把比赛拖入大将战。"
    )


def team_name_for_player(report: BattleReport, raw_name: str) -> str | None:
    for team in (report.team_a, report.team_b):
        if any(player.raw_name == raw_name for player in team.players):
            return team.display_name
    return None


def _round_streak(round_item: Round) -> tuple[str | None, int]:
    best_name: str | None = None
    best = 0
    current_name: str | None = None
    current = 0
    for game in round_item.matches:
        if game.winner_display == current_name:
            current += 1
        else:
            current_name = game.winner_display
            current = 1
        if current > best:
            best = current
            best_name = current_name
    return best_name, best


def format_date(report: BattleReport) -> str:
    if not report.match_date:
        return "今日"
    return report.match_date.strftime("%Y年%m月%d日")
