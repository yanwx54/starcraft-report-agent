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
    used_comments: set[str] = set()
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
        comment = rating_comment(stat, score, used_comments)
        used_comments.add(comment)
        ratings.append(PlayerRating(stat=stat, score=score, tag=rating_tag(score), comment=comment))

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


def rating_comment(stat: PlayerStat, score: float, used_comments: set[str] | None = None) -> str:
    record = f"{stat.wins}胜{stat.losses}负"
    if score >= 9.5:
        return choose_comment(
            stat,
            [
                f"{record}，今晚就是大腿本腿。队友先别复盘，先给他倒水。",
                f"{record}，硬得不像话，队伍节奏基本靠他顶住。",
                f"{record}，从开局到收尾都够狠，评分高一点不过分。",
            ],
            used_comments,
        )
    if score >= 8.5:
        return choose_comment(
            stat,
            [
                f"{record}，关键局没手软。这种表现，赛后评分低不了。",
                f"{record}，该站出来的时候真站了，赢面就是这么抬起来的。",
                f"{record}，存在感很足，对面想绕都绕不开。",
            ],
            used_comments,
        )
    if score >= 7.0:
        return choose_comment(
            stat,
            [
                f"{record}，该拿的分拿了，至少没让队伍难受。",
                f"{record}，不算炸场，但关键拼图这一块补上了。",
                f"{record}，打得挺实在，队友需要的分他给到了。",
            ],
            used_comments,
        )
    if score >= 5.8:
        return choose_comment(
            stat,
            [
                f"{record}，存在感一般。赢了能笑，输了也别喊冤。",
                f"{record}，功过放一起看，今天就是中间档。",
                f"{record}，有贡献也有遗憾，分数先给个保守评价。",
            ],
            used_comments,
        )
    if score >= 4.5:
        return choose_comment(
            stat,
            [
                f"{record}，这表现有点伤，复盘室里少不了他的名字。",
                f"{record}，节奏没咬住，队伍压力跟着变大了。",
                f"{record}，不是完全没内容，但丢分位置太显眼。",
            ],
            used_comments,
        )
    if score >= 3.2:
        return choose_comment(
            stat,
            [
                f"{record}，锅已经热了，自己端稳。",
                f"{record}，今天被点得有点狠，下场得把手感找回来。",
                f"{record}，关键分没守住，赛后估计得多看两遍录像。",
            ],
            used_comments,
        )
    return choose_comment(
        stat,
        [
            f"{record}，今晚评论区别看了，越看越闹心。",
            f"{record}，这分数不用解释，场面已经替他说完了。",
            f"{record}，想翻身只能等下一场重新打回来。",
        ],
        used_comments,
    )


def choose_comment(stat: PlayerStat, candidates: list[str], used_comments: set[str] | None) -> str:
    used = used_comments or set()
    start = stable_comment_index(stat, len(candidates))
    for offset in range(len(candidates)):
        candidate = candidates[(start + offset) % len(candidates)]
        if candidate not in used:
            return candidate
    return f"{stat.display_name}单独看：{candidates[start]}"


def stable_comment_index(stat: PlayerStat, count: int) -> int:
    seed = f"{stat.raw_name}|{stat.display_name}|{stat.wins}|{stat.losses}|{stat.max_streak}"
    return sum(ord(char) for char in seed) % count if count else 0
