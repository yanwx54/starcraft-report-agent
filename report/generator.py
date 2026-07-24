from __future__ import annotations

import json
import re
from dataclasses import dataclass

from models import BattleReport, PlayerStat, Round
from translator.deepseek import DeepSeekTranslator


WECHAT_TITLE_MAX_CHARS = 25
AI_SLOP_REPLACEMENTS = {
    "最终宣判：": "说到最后，",
    "最终宣判": "说到最后",
    "真正的胜负手出现在": "胜负手在",
    "关键性的": "关键的",
    "至关重要": "很要紧",
    "彰显": "打出",
    "体现": "看得出",
    "证明": "说明",
    "格局": "局面",
    "不可磨灭的印记": "记忆点",
    "天神下凡级别的": "很硬的",
    "无情碾压": "压得很狠",
}


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
        "你是一位顶级电竞专栏作家，负责运营爆款《星际争霸：重制版》微信公众号。"
        "受众是中国星际老粉，喜欢激情、抓马、情怀和辛辣点评。"
        "本文采用激昂/解说流 Excited 风格，但要像真人老粉复盘，不要像模板营销文。"
        "可以有火气、有梗、有短句，但每段都要落在具体比分、连胜、地图和选手身上。"
        "可少量使用“炸裂”“封神”“白给”“没道理的”等电竞表达，但不要堆热词。"
        "emoji 全文最多 2 个，标题不要 emoji。"
        "但只能基于结构化赛果写作：没有录像数据，不得编造具体战术细节、APM 数值、心理活动或不存在的神仙操作。"
        "严禁自己脑补比赛过程：不要写 rush、运营、扩张、兵种细节、极限操作、APM、经济线、空投、偷家等未出现在结构化赛果里的内容。"
        "可以写的只有：谁赢谁输、地图、轮次比分、同一轮内连续胜利、被终结、收官局、大将战抽签模式和最终比分。"
        "地图名必须使用输入中的中文翻译名，选手名和队名使用输入中的显示名。"
        "必须聚焦团队赛：团队总比分、轮次比分、连胜、转折点、最后收官局或大将战是文章核心。"
        "去除 AI 写作痕迹：少用“最终宣判”“至关重要”“彰显”“体现”“证明”“格局”“不仅……而且……”等套话；"
        "不要机械三段式，不要每段都用同样句式结尾，不要把简单事实拔高成宏大意义。"
        "相信读者懂星际，少解释口号，多写具体赛果和你作为作者的判断。"
        "如果结构化赛果中 has_ace_match 为 true，必须写大将战，严禁写未进行大将战、无需大将战或由前两轮决定。"
        "如果 has_ace_match 为 false，才可以写未进行大将战。"
        "必须返回严格 JSON，不要 Markdown，不要代码块。"
    )
    user = (
        "请生成一篇韩国星际争霸团战公众号战报草稿。JSON 字段必须包含："
        "title、intro、round_reviews、mvp_text、summary。"
        f"title 必须适合公众号推送，最多 {WECHAT_TITLE_MAX_CHARS} 个字符。"
        "round_reviews 是数组，长度必须与 rounds 一致，每项包含 name 和 text。"
        "intro 约90-130字，第一句打出结果和最大看点，不要写空泛金句。"
        "round text 不要机械罗列每局，但只能把结构化赛果串成自然复盘，突出首轮一血、单轮连胜、被终结、收官局等转折。"
        "mvp_text 要给出获胜方/全场大功臣，也可以点出败方最伤的一环，但措辞保持电竞吐槽感，不做人身攻击。"
        "summary 约150-230字，像公众号作者收尾点评：直接、有态度、有一两个具体判断。"
        "避免“首先/其次/最后/此外/然而/综上”“这不仅仅是……而是……”等 AI 连接句。"
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
        article = humanize_article(article)
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
        f"🔥 MVP 给到{mvp.display_name}！{mvp.wins}胜{mvp.losses}负，最长{mvp.max_streak}连胜，"
        "这就是今天最硬的战绩单。"
        f"{fall_guy_text(report)}"
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


def humanize_article(article: GeneratedArticle) -> GeneratedArticle:
    return GeneratedArticle(
        title=strip_emojis(humanize_text(article.title)),
        intro=humanize_text(article.intro),
        round_reviews=[(name, humanize_text(text)) for name, text in article.round_reviews],
        mvp=article.mvp,
        mvp_text=humanize_text(article.mvp_text),
        summary=humanize_text(article.summary),
        ai_generated=article.ai_generated,
    )


def humanize_text(text: str) -> str:
    for source, target in AI_SLOP_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"这不(?:仅|只是|仅仅)是([^，。；]+)[，,]而是([^。；]+)", r"这更像是\2", text)
    text = re.sub(r"(此外|然而|综上)[，,]", "", text)
    text = re.sub(r"([！!]){2,}", "！", text)
    text = re.sub(r"([。；])\s+", r"\1", text)
    return text.strip()


def strip_emojis(text: str) -> str:
    return re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", text).strip()


def build_article_payload(report: BattleReport, mvp: PlayerStat) -> dict[str, object]:
    ace_match = report.ace_round.matches[0] if report.ace_round and report.ace_round.matches else None
    fall_guy = choose_fall_guy(report)
    return {
        "match_id": report.match_id,
        "date": report.match_date.isoformat() if report.match_date else "",
        "league": report.league_name,
        "score": f"{report.team_a.display_name} {report.score_text} {report.team_b.display_name}",
        "has_ace_match": bool(ace_match),
        "ace_mode": report.ace_round.ace_mode if report.ace_round else "",
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
        "fall_guy_candidate": {
            "name": fall_guy.display_name,
            "race": fall_guy.race,
            "team": fall_guy.team,
            "wins": fall_guy.wins,
            "losses": fall_guy.losses,
            "max_streak": fall_guy.max_streak,
        }
        if fall_guy
        else None,
        "player_stats": [
            {
                "name": player.display_name,
                "team": player.team,
                "race": player.race,
                "wins": player.wins,
                "losses": player.losses,
                "max_streak": player.max_streak,
                "closing_win": player.closing_win,
            }
            for player in report.player_stats
        ],
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

    winner_team = round_item.winner_team or winning_team_name(report, round_item)
    lead = f"{round_item.name}，{winner_team}打出{round_item.score_a}:{round_item.score_b}。"
    winners = [game.winner_display for game in round_item.matches]
    streak_player, streak = _round_streak(round_item)
    highlights: list[str] = []
    if winners:
        highlights.append(f"本轮胜场来自{'、'.join(winners)}。")
    if streak_player and streak >= 2:
        highlights.append(f"{streak_player}在这一轮打出{streak}连胜，这是本轮最醒目的转折。")
    closing = round_item.matches[-1]
    opponent = closing.player_b.display_name if closing.winner == closing.player_a.raw_name else closing.player_a.display_name
    highlights.append(f"最后一局在{closing.map_name}，{closing.winner_display}击败{opponent}，为本轮收官。")
    return lead + "".join(highlights)


def sanitize_article(report: BattleReport, article: GeneratedArticle, fallback: GeneratedArticle) -> GeneratedArticle:
    round_reviews: list[tuple[str, str]] = []
    provided = article.round_reviews or []
    for index, round_item in enumerate(report.all_rounds):
        text = ""
        if index < len(provided):
            text = provided[index][1].strip()
        if (
            not text
            or has_fact_conflict(report, text)
            or has_unsupported_process_detail(report, text)
            or (is_ace_round(round_item) and misses_ace_round_facts(round_item, text))
        ):
            text = describe_round(report, round_item)
        round_reviews.append((round_item.name, text))

    title = article.title.strip() or fallback.title
    intro = article.intro.strip() or fallback.intro
    summary = article.summary.strip() or fallback.summary
    mvp_text = article.mvp_text.strip() or fallback.mvp_text

    if has_fact_conflict(report, title) or has_unsupported_process_detail(report, title):
        title = fallback.title
    if len(title) > WECHAT_TITLE_MAX_CHARS:
        title = build_short_title(report, article.mvp)
    if has_fact_conflict(report, intro) or has_unsupported_process_detail(report, intro) or misses_required_ace(report, intro):
        intro = fallback.intro
    if has_fact_conflict(report, summary) or has_unsupported_process_detail(report, summary) or misses_required_ace(report, summary):
        summary = fallback.summary
    if has_fact_conflict(report, mvp_text) or has_unsupported_process_detail(report, mvp_text):
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


def has_unsupported_process_detail(report: BattleReport, text: str) -> bool:
    raw = report.raw_text.lower()
    forbidden_terms = (
        "apm",
        "rush",
        "运营",
        "扩张",
        "开矿",
        "经济线",
        "空投",
        "偷家",
        "兵种",
        "极限操作",
        "神仙操作",
        "多线",
        "拉扯",
        "侦查",
        "雷车",
        "坦克",
        "龙骑",
        "航母",
        "飞龙",
        "地刺",
    )
    lowered = text.lower()
    return any(term.lower() in lowered and term.lower() not in raw for term in forbidden_terms)


def misses_ace_round_facts(round_item: Round, text: str) -> bool:
    if not round_item.matches:
        return False
    game = round_item.matches[-1]
    return game.map_name not in text or game.winner_display not in text


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
    mode = f"{round_item.ace_mode}，" if round_item.ace_mode else ""
    return (
        f"🔥 大将战来了，{mode}{winner_player.display_name}({winner_player.race})"
        f"在{game.map_name}地图上击败{loser_player.display_name}({loser_player.race})，"
        f"帮{winner_team}把决胜局硬生生拿下！最终总比分定格为{report.team_a.display_name} {report.score_text} {report.team_b.display_name}。"
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
            f"炸裂！{date_text}的{report.league_name}直接打到大将战！{winner}和{loser}前两轮杀成1:1，"
            f"{report.ace_round.ace_mode + '，' if report.ace_round and report.ace_round.ace_mode else ''}"
            f"最后{ace.winner_display}在{ace.map_name}收官，帮{winner}以"
            f"{report.winner_team.score}:{report.loser_team.score}惊险封神！"
            f"{mvp.display_name}{mvp.wins}胜{mvp.losses}负，今天这存在感拉满！"
        )
    return (
        f"无情碾压！{date_text}的{report.league_name}，{winner}以"
        f"{report.winner_team.score}:{report.loser_team.score}击败{loser}！"
        f"{mvp.display_name}直接打出{mvp.wins}胜{mvp.losses}负、最长{mvp.max_streak}连胜，"
        "这波就是天神下凡级别的团队赛输出！"
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
            f"最终宣判：这场比赛就是一部团战爽剧！{base}，前两轮打成1:1，悬念直接拉满。"
            f"真正的胜负手出现在大将战，{report.ace_round.ace_mode + '，' if report.ace_round and report.ace_round.ace_mode else ''}"
            f"{ace.winner_display}在{ace.map_name}一锤定音，"
            f"为{winner}锁死{report.winner_team.score}:{report.loser_team.score}！"
            f"{mvp.display_name}{mvp.wins}胜{mvp.losses}负、最长{mvp.max_streak}连胜已经够炸，"
            f"但{winner}最后这口气更硬，关键局就是不手软！"
        )
    return (
        f"最终宣判：{winner}这场就是无情碾压！{base}，总比分"
        f"{report.winner_team.score}:{report.loser_team.score}带走{loser}。"
        f"{mvp.display_name}{mvp.wins}胜{mvp.losses}负、最长{mvp.max_streak}连胜，"
        f"堪称本场最炸火力点。{loser}不是没有挣扎，但没能把比赛拖进大将战，节奏被彻底按住了！"
    )


def team_name_for_player(report: BattleReport, raw_name: str) -> str | None:
    for team in (report.team_a, report.team_b):
        if any(player.raw_name == raw_name for player in team.players):
            return team.display_name
    return None


def choose_fall_guy(report: BattleReport) -> PlayerStat | None:
    loser_players = [player for player in report.player_stats if player.team == report.loser_team.display_name]
    if not loser_players:
        return None
    return sorted(
        loser_players,
        key=lambda player: (player.losses, player.losses - player.wins, -player.wins),
        reverse=True,
    )[0]


def fall_guy_text(report: BattleReport) -> str:
    player = choose_fall_guy(report)
    if not player or player.losses == 0:
        return ""
    return f" 败方这边，{player.display_name}{player.wins}胜{player.losses}负有点伤，今天真得背点锅。"


def winning_team_name(report: BattleReport, round_item: Round) -> str:
    if round_item.winner_team:
        return round_item.winner_team
    return report.team_a.display_name if round_item.score_a >= round_item.score_b else report.team_b.display_name


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
