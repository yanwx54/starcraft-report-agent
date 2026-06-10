export enum Race {
  Z = 'Z',
  T = 'T',
  P = 'P',
  Unknown = 'U'
}

export interface PlayerStats {
  name: string;
  race: Race;
  wins: number;
  losses: number;
  prizeMoney: number;
  team: string;
}

export interface Match {
  id: number;
  map: string;
  playerA: string;
  raceA: Race;
  resultA: 'Win' | 'Loss';
  playerB: string;
  raceB: Race;
  resultB: 'Win' | 'Loss';
  winnerName: string;
}

export interface Round {
  name: string;
  matches: Match[];
  scoreA: number;
  scoreB: number;
  winnerTeam: string | null;
}

export interface TeamData {
  name: string;
  players: string[];
  totalScore: number;
  isWinner: boolean;
}

export interface BattleReportData {
  title: string;
  date: string;
  teamA: TeamData;
  teamB: TeamData;
  prizePool: number;
  rounds: Round[];
  aceMatch: Round | null;
  playerStats: PlayerStats[];
}