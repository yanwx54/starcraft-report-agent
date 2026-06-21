from __future__ import annotations

from dataclasses import dataclass

from models import BattleReport, PlayerStat


@dataclass
class PlayerRating:
    stat: PlayerStat
    score: float
    tag: str
    comment: str


def build_ratings(report: BattleReport) -> list[PlayerRating]:
    ace_winner = ""
    ace_loser = ""
    if report.ace_round and report.ace_round.matches:
        game = report.ace_round.matches[-1]
        ace_winner = game.winner
        ace_loser = game.player_b.raw_name if game.winner == game.player_a.raw_name else game.player_a.raw_name

    ratings: list[PlayerRating] = []
    for stat in report.player_stats:
        score = 6.0
        score += stat.wins * 0.9
        score -= stat.losses * 0.8
        score += max(stat.max_streak - 1, 0) * 0.25
        if stat.closing_win:
            score += 0.4
        if stat.raw_name == ace_winner:
            score += 1.0
        if stat.raw_name == ace_loser:
            score -= 1.0
        score += 0.3 if stat.team == report.winner_team.display_name else -0.2
        score = max(2.0, min(9.9, round(score, 1)))
        ratings.append(PlayerRating(stat=stat, score=score, tag=rating_tag(score), comment=rating_comment(stat, score)))

    return sorted(ratings, key=lambda item: (item.score, item.stat.wins, -item.stat.losses), reverse=True)


def rating_tag(score: float) -> str:
    if score >= 9.5:
        return "封神"
    if score >= 8.5:
        return "大腿"
    if score >= 7.0:
        return "够硬"
    if score >= 5.8:
        return "还行"
    if score >= 4.5:
        return "有点伤"
    if score >= 3.2:
        return "背锅"
    return "战犯级"


def rating_comment(stat: PlayerStat, score: float) -> str:
    if score >= 9.5:
        return f"{stat.wins}胜{stat.losses}负，今晚就是大腿本腿。队友先别复盘，先给他倒水。"
    if score >= 8.5:
        return f"{stat.wins}胜{stat.losses}负，关键局没手软。这种表现，赛后评分低不了。"
    if score >= 7.0:
        return f"{stat.wins}胜{stat.losses}负，该拿的分拿了，至少没让队伍难受。"
    if score >= 5.8:
        return f"{stat.wins}胜{stat.losses}负，存在感一般。赢了能笑，输了也别喊冤。"
    if score >= 4.5:
        return f"{stat.wins}胜{stat.losses}负，这表现有点伤，复盘室里少不了他的名字。"
    if score >= 3.2:
        return f"{stat.wins}胜{stat.losses}负，锅已经热了，自己端稳。"
    return f"{stat.wins}胜{stat.losses}负，今晚评论区别看了，越看越闹心。"
