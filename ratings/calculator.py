from __future__ import annotations

from dataclasses import dataclass

from models import BattleReport, PlayerStat


@dataclass
class PlayerRating:
    stat: PlayerStat
    score: float


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
        ratings.append(PlayerRating(stat=stat, score=score))

    return sorted(ratings, key=lambda item: (item.score, item.stat.wins, -item.stat.losses), reverse=True)
