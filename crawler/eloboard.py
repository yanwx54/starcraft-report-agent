from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import settings
from models import BattleReport, MatchGame, PlayerRef, PlayerStat, Round, Team
from translator.rules import TranslateRules, compact_korean_name, load_translate_rules


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StarCraftReportAgent/1.0"


@dataclass
class MatchSummary:
    match_id: str
    title: str
    url: str
    match_date: date | None


class ELOBoardClient:
    def __init__(self, rules: TranslateRules | None = None) -> None:
        self.rules = rules or load_translate_rules()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=25)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response.text

    def list_matches(self, url: str | None = None, limit: int = 10) -> list[MatchSummary]:
        page_url = url or settings.eloboard_list_url
        soup = BeautifulSoup(self.fetch_html(page_url), "html.parser")
        seen: set[str] = set()
        matches: list[MatchSummary] = []
        for link in soup.select('a[href*="bo_table=pro_league"][href*="wr_id="]'):
            href = urljoin(page_url, link.get("href", ""))
            match_id = extract_wr_id(href)
            if not match_id or match_id in seen:
                continue
            title = link.get_text(" ", strip=True)
            if not title:
                continue
            seen.add(match_id)
            matches.append(
                MatchSummary(
                    match_id=match_id,
                    title=normalize_spaces(title),
                    url=href,
                    match_date=parse_date(title),
                )
            )
            if len(matches) >= limit:
                break
        return matches

    def latest_match(self) -> MatchSummary:
        matches = self.list_matches(limit=30)
        if not matches:
            raise RuntimeError("未在 ELOBoard 列表页找到团战记录")
        return choose_daily_match(matches)

    def fetch_match(self, match_id_or_url: str | None = None) -> BattleReport:
        if not match_id_or_url:
            summary = self.latest_match()
            url = summary.url
            match_id = summary.match_id
        elif match_id_or_url.startswith("http"):
            url = match_id_or_url
            match_id = extract_wr_id(url) or match_id_or_url.rsplit("=", 1)[-1]
        else:
            match_id = match_id_or_url
            url = f"{settings.eloboard_list_url}&wr_id={match_id}"

        html = self.fetch_html(url)
        return parse_match_detail(html, url=url, match_id=match_id, rules=self.rules)


def parse_match_detail(html: str, url: str, match_id: str, rules: TranslateRules | None = None) -> BattleReport:
    rules = rules or load_translate_rules()
    soup = BeautifulSoup(html, "html.parser")
    title = normalize_spaces((soup.title.get_text(" ", strip=True) if soup.title else "").split(">")[0])
    if not title:
        h1 = soup.find(["h1", "h2"])
        title = normalize_spaces(h1.get_text(" ", strip=True) if h1 else f"pro_league {match_id}")

    content_node = soup.select_one("article") or soup.select_one(".view-content") or soup.body
    raw_text = content_node.get_text(" ", strip=True) if content_node else soup.get_text(" ", strip=True)
    text = normalize_detail_text(raw_text)

    race_map = parse_race_map(text)
    team_a, team_b = parse_teams(text, rules, race_map)
    prize_text = parse_prize_text(text)
    rounds, ace_round = parse_rounds(text, rules, race_map, team_a, team_b)
    apply_scores(text, team_a, team_b, rounds, ace_round)
    stats = calculate_player_stats(team_a, team_b, rounds, ace_round)
    team_a.is_winner = team_a.score > team_b.score
    team_b.is_winner = team_b.score > team_a.score

    return BattleReport(
        match_id=match_id,
        source_url=url,
        title_raw=title,
        match_date=parse_date(title) or parse_date(text),
        league_name=parse_league_name(title),
        prize_text=prize_text,
        team_a=team_a,
        team_b=team_b,
        rounds=rounds,
        ace_round=ace_round,
        player_stats=stats,
        raw_text=text,
    )


def extract_wr_id(url: str) -> str | None:
    parsed = urlparse(url)
    return parse_qs(parsed.query).get("wr_id", [None])[0]


def choose_daily_match(matches: list[MatchSummary]) -> MatchSummary:
    dated_matches = [match for match in matches if match.match_date]
    if not dated_matches:
        return matches[0]

    latest_date = max(match.match_date for match in dated_matches)
    same_day = [match for match in dated_matches if match.match_date == latest_date]
    if len(same_day) == 1:
        return same_day[0]

    return sorted(same_day, key=league_priority)[0]


def league_priority(match: MatchSummary) -> tuple[int, int]:
    title = match.title
    if "메이저" in title and "준메이저" not in title:
        league_rank = 0
    elif "준메이저" in title:
        league_rank = 1
    elif "K리그" in title:
        league_rank = 2
    else:
        league_rank = 3
    try:
        id_rank = -int(match.match_id)
    except ValueError:
        id_rank = 0
    return league_rank, id_rank


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_detail_text(text: str) -> str:
    text = normalize_spaces(text)
    text = re.sub(r"\[\s+", "[", text)
    text = re.sub(r"\s+\]", "]", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s*:\s*", " : ", text)
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\b([가-힣])\s+([가-힣]{1,2})([ZTP])\b", r"\1\2\3", text)
    text = re.sub(r"\b([가-힣])\s+([가-힣]{1,2})(?=\s*(?:팀|\(|\[|vs|$))", r"\1\2", text)
    text = re.sub(r"위너스\s+리그", "위너스리그", text)
    text = re.sub(r"윤중\s+팀", "윤중팀", text)
    text = re.sub(r"(\d+)\s+\.\s+", r"\1. ", text)
    return normalize_spaces(text)


def parse_date(text: str) -> date | None:
    match = re.search(r"(20\d{2})[.\-년/]\s*(\d{1,2})[.\-월/]\s*(\d{1,2})", text)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_league_name(title: str) -> str:
    cleaned = re.sub(r"20\d{2}[.\-]\d{1,2}[.\-]\d{1,2}\s*\([^)]*\)\s*", "", title)
    cleaned = normalize_spaces(cleaned)
    replacements = {
        "스타": "星际争霸",
        "메이저": "Major",
        "준메이저": "准Major",
        "프로리그": "职业联赛",
        "K리그": "K联赛",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return normalize_spaces(cleaned) or "韩国星际争霸团战"


def parse_prize_text(text: str) -> str:
    winners = re.findall(r"승자\d+\s*([가-힣]+)\s*\(([^)]+)\)", text)
    if winners:
        return winners[0][1].replace("\\", "₩")
    total = re.search(r"(?:두|총|合计|总计)\s*([0-9,]+)\s*개", text)
    return f"{total.group(1)}个" if total else ""


def parse_race_map(text: str) -> dict[str, str]:
    race_map: dict[str, str] = {}
    for race in ("Z", "P", "T"):
        match = re.search(rf"(?:^|\s){race}\s+(.+?)(?=\s+[ZPT]\s+|\s+\[[^\]]+팀\]|\s+\[\d+SET|\s+\d+\.\s+\[|$)", text)
        if not match:
            continue
        for name in re.findall(r"[가-힣]{2,4}", match.group(1)):
            race_map[compact_korean_name(name)] = race
    return race_map


def parse_teams(text: str, rules: TranslateRules, race_map: dict[str, str]) -> tuple[Team, Team]:
    team_matches = list(re.finditer(r"\[([^\]]+팀)\]\s+(.+?)(?=\s+\[[^\]]+팀\]|\s+\[\d+SET|\s+\d+\.\s+\[|$)", text))
    teams: list[Team] = []
    for match in team_matches[:2]:
        raw_name = compact_korean_name(match.group(1))
        raw_players = [compact_korean_name(name) for name in re.findall(r"[가-힣]{2,4}", match.group(2))]
        players = [
            PlayerRef(
                raw_name=player,
                display_name=rules.translate_player(player),
                race=race_map.get(player, "U"),
            )
            for player in raw_players
        ]
        teams.append(Team(raw_name=raw_name, display_name=rules.translate_player(raw_name.replace("팀", "")) + "队", players=players))

    if len(teams) < 2:
        teams = [
            Team(raw_name="TeamA", display_name="Team A"),
            Team(raw_name="TeamB", display_name="Team B"),
        ]
    return teams[0], teams[1]


ROUND_HEADER_RE = re.compile(r"\[(\d+SET\s*-\s*.*?)(?:\]|\s+\])")


def parse_rounds(
    text: str,
    rules: TranslateRules,
    race_map: dict[str, str],
    team_a: Team,
    team_b: Team,
) -> tuple[list[Round], Round | None]:
    headers = list(ROUND_HEADER_RE.finditer(text))
    rounds: list[Round] = []
    ace_round: Round | None = None
    for index, header in enumerate(headers):
        start = header.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[start:end]
        name = normalize_round_name(header.group(1))
        current_round = Round(name=name)
        current_round.matches = parse_games(body, rules, race_map)
        parse_round_score(body, current_round, team_a, team_b)
        infer_round_score_from_matches(current_round, team_a, team_b)
        if "Super Ace" in name or "슈에" in body:
            ace_round = current_round
        else:
            rounds.append(current_round)
    return rounds, ace_round


def normalize_round_name(name: str) -> str:
    name = normalize_spaces(name)
    name = name.replace("1SET", "第一轮").replace("2SET", "第二轮").replace("3SET", "大将战")
    name = name.replace("프로리그", "职业联赛制").replace("위너스리그", "胜者联赛制")
    name = name.replace("Super Ace Match", "Super Ace Match")
    return name


GAME_RE = re.compile(
    r"(?:(\d+)\.\s*)?\[([^\]]+)\]\s*"
    r"(.+?)([ZTP])\s*\((승|패)\)\s*vs\s*\((승|패)\)\s*"
    r"(.+?)([ZTP])(?=\s+(?:\d+\.\s*)?\[|\s+[가-힣A-Za-z0-9\s]+팀\s*\(|\s+최종 결과|$)"
)


def parse_games(body: str, rules: TranslateRules, race_map: dict[str, str]) -> list[MatchGame]:
    games: list[MatchGame] = []
    for match in GAME_RE.finditer(body):
        idx = int(match.group(1)) if match.group(1) else len(games) + 1
        map_name = rules.translate_map(match.group(2))
        raw_a = compact_korean_name(match.group(3))
        race_a = match.group(4)
        result_a = match.group(5)
        result_b = match.group(6)
        raw_b = compact_korean_name(match.group(7))
        race_b = match.group(8)
        race_map[raw_a] = race_a
        race_map[raw_b] = race_b
        winner_raw = raw_a if result_a == "승" and result_b == "패" else raw_b
        games.append(
            MatchGame(
                id=idx,
                map_name=map_name,
                player_a=PlayerRef(raw_a, rules.translate_player(raw_a), race_a),
                player_b=PlayerRef(raw_b, rules.translate_player(raw_b), race_b),
                winner=winner_raw,
                winner_display=rules.translate_player(winner_raw),
            )
        )
    return games


def parse_round_score(body: str, current_round: Round, team_a: Team, team_b: Team) -> None:
    pattern = re.compile(
        r"([가-힣A-Za-z0-9\s]+팀)\s*\((승|패)\)\s*(\d+)\s*:\s*(\d+)\s*\((승|패)\)\s*([가-힣A-Za-z0-9\s]+팀)"
    )
    match = pattern.search(body)
    if not match:
        return
    left_team, left_result, left_score, right_score, _right_result, right_team = match.groups()
    left_score_i, right_score_i = int(left_score), int(right_score)
    if compact_korean_name(left_team) == team_a.raw_name:
        current_round.score_a, current_round.score_b = left_score_i, right_score_i
    elif compact_korean_name(left_team) == team_b.raw_name:
        current_round.score_b, current_round.score_a = left_score_i, right_score_i
    else:
        current_round.score_a, current_round.score_b = left_score_i, right_score_i
    winner_raw = left_team if left_result == "승" else right_team
    if compact_korean_name(winner_raw) == team_a.raw_name:
        current_round.winner_team = team_a.display_name
    elif compact_korean_name(winner_raw) == team_b.raw_name:
        current_round.winner_team = team_b.display_name


def infer_round_score_from_matches(current_round: Round, team_a: Team, team_b: Team) -> None:
    if not current_round.matches:
        return

    if current_round.score_a or current_round.score_b:
        if not current_round.winner_team:
            if current_round.score_a > current_round.score_b:
                current_round.winner_team = team_a.display_name
            elif current_round.score_b > current_round.score_a:
                current_round.winner_team = team_b.display_name
        return

    team_a_names = {player.raw_name for player in team_a.players}
    team_b_names = {player.raw_name for player in team_b.players}
    score_a = 0
    score_b = 0
    for game in current_round.matches:
        if game.winner in team_a_names:
            score_a += 1
        elif game.winner in team_b_names:
            score_b += 1

    current_round.score_a = score_a
    current_round.score_b = score_b
    if score_a > score_b:
        current_round.winner_team = team_a.display_name
    elif score_b > score_a:
        current_round.winner_team = team_b.display_name


def apply_scores(text: str, team_a: Team, team_b: Team, rounds: list[Round], ace_round: Round | None) -> None:
    final = re.search(r"최종 결과\s+([가-힣A-Za-z0-9]+팀)\s+(\d+)\s*:\s*(\d+)\s*승", text)
    if final:
        winner_raw, win_score, lose_score = final.groups()
        if compact_korean_name(winner_raw) == team_a.raw_name:
            team_a.score, team_b.score = int(win_score), int(lose_score)
        else:
            team_b.score, team_a.score = int(win_score), int(lose_score)
        return

    all_rounds = [*rounds, *([ace_round] if ace_round else [])]
    team_a.score = sum(1 for item in all_rounds if item.winner_team == team_a.display_name)
    team_b.score = sum(1 for item in all_rounds if item.winner_team == team_b.display_name)


def calculate_player_stats(team_a: Team, team_b: Team, rounds: list[Round], ace_round: Round | None) -> list[PlayerStat]:
    stats: dict[str, PlayerStat] = {}

    def init(player: PlayerRef, team: Team) -> None:
        stats.setdefault(
            player.raw_name,
            PlayerStat(player.raw_name, player.display_name, team.display_name, player.race),
        )

    for player in team_a.players:
        init(player, team_a)
    for player in team_b.players:
        init(player, team_b)

    streaks: dict[str, int] = {name: 0 for name in stats}
    all_games = [game for round_item in [*rounds, *([ace_round] if ace_round else [])] for game in round_item.matches]
    for index, game in enumerate(all_games):
        for player in (game.player_a, game.player_b):
            if player.raw_name not in stats:
                team = team_a if any(p.raw_name == player.raw_name for p in team_a.players) else team_b
                stats[player.raw_name] = PlayerStat(player.raw_name, player.display_name, team.display_name, player.race)
                streaks[player.raw_name] = 0

        loser = game.player_b.raw_name if game.winner == game.player_a.raw_name else game.player_a.raw_name
        stats[game.winner].wins += 1
        stats[loser].losses += 1
        streaks[game.winner] = streaks.get(game.winner, 0) + 1
        streaks[loser] = 0
        stats[game.winner].max_streak = max(stats[game.winner].max_streak, streaks[game.winner])
        if index == len(all_games) - 1:
            stats[game.winner].closing_win = True

    return list(stats.values())


def iter_matches(report: BattleReport) -> Iterable[MatchGame]:
    for round_item in report.all_rounds:
        yield from round_item.matches
