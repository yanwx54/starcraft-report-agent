from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Literal


Race = Literal["Z", "T", "P", "U"]


@dataclass
class PlayerRef:
    raw_name: str
    display_name: str
    race: Race = "U"


@dataclass
class MatchGame:
    id: int
    map_name: str
    player_a: PlayerRef
    player_b: PlayerRef
    winner: str
    winner_display: str


@dataclass
class Round:
    name: str
    matches: list[MatchGame] = field(default_factory=list)
    score_a: int = 0
    score_b: int = 0
    winner_team: str | None = None
    ace_mode: str = ""


@dataclass
class Team:
    raw_name: str
    display_name: str
    players: list[PlayerRef] = field(default_factory=list)
    score: int = 0
    is_winner: bool = False


@dataclass
class PlayerStat:
    raw_name: str
    display_name: str
    team: str
    race: Race
    wins: int = 0
    losses: int = 0
    closing_win: bool = False
    max_streak: int = 0

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total else 0.0


@dataclass
class BattleReport:
    match_id: str
    source_url: str
    title_raw: str
    match_date: date | None
    league_name: str
    prize_text: str
    team_a: Team
    team_b: Team
    rounds: list[Round]
    ace_round: Round | None = None
    player_stats: list[PlayerStat] = field(default_factory=list)
    raw_text: str = ""

    @property
    def score_text(self) -> str:
        return f"{self.team_a.score}:{self.team_b.score}"

    @property
    def winner_team(self) -> Team:
        return self.team_a if self.team_a.is_winner else self.team_b

    @property
    def loser_team(self) -> Team:
        return self.team_b if self.team_a.is_winner else self.team_a

    @property
    def all_rounds(self) -> list[Round]:
        return [*self.rounds, *([self.ace_round] if self.ace_round else [])]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
