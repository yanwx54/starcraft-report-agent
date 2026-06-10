import React from 'react';
import { Match, Round, Race } from '../types';

interface Props {
  round: Round;
  index: number;
  teamAName: string;
  teamBName: string;
}

const RaceBadge: React.FC<{ race: Race }> = ({ race }) => {
  const styles = {
    [Race.P]: 'border-yellow-500/40 text-yellow-400 bg-yellow-900/20',
    [Race.T]: 'border-blue-500/40 text-blue-400 bg-blue-900/20',
    [Race.Z]: 'border-purple-500/40 text-purple-400 bg-purple-900/20',
    [Race.Unknown]: 'border-gray-500/40 text-gray-400 bg-gray-900/20'
  }[race];

  return (
    <div className={`w-8 h-8 flex items-center justify-center text-sm font-bold border rounded ${styles}`}>
      {race}
    </div>
  );
};

const ResultLabel: React.FC<{ isWin: boolean }> = ({ isWin }) => (
  <span className={`font-black text-xl italic uppercase tracking-wider ${isWin ? 'text-green-500 drop-shadow-[0_0_5px_rgba(34,197,94,0.5)]' : 'text-slate-500'}`}>
    {isWin ? 'WIN' : 'LOSE'}
  </span>
);

const MatchRow: React.FC<{ match: Match }> = ({ match }) => {
  const aWon = match.resultA === 'Win';
  
  // Helper for Race text colors
  const getRaceTextColor = (race: Race) => {
    switch(race) {
        case Race.P: return 'text-yellow-400';
        case Race.T: return 'text-blue-400';
        case Race.Z: return 'text-purple-400';
        default: return 'text-white';
    }
  };

  return (
    <div className="flex items-center justify-between py-4 px-5 bg-slate-800/40 border border-slate-700/50 rounded-lg mb-3 relative overflow-hidden group hover:border-slate-600 transition-all">
      {/* Center Map Name */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center opacity-40 group-hover:opacity-100 transition-opacity">
        <span className="text-xs uppercase tracking-widest text-slate-400 mb-0.5">Game {match.id}</span>
        <span className="text-sm font-bold text-white whitespace-nowrap">{match.map}</span>
      </div>

      {/* Player A (Left) */}
      <div className={`flex items-center gap-3 w-5/12 ${aWon ? '' : 'opacity-50 grayscale'}`}>
        <RaceBadge race={match.raceA} />
        <span className={`font-bold text-2xl font-sc truncate ${getRaceTextColor(match.raceA)}`}>
            {match.playerA}
        </span>
        <ResultLabel isWin={aWon} />
      </div>

      {/* Player B (Right) */}
      <div className={`flex items-center gap-3 w-5/12 justify-end ${!aWon ? '' : 'opacity-50 grayscale'}`}>
        <ResultLabel isWin={!aWon} />
        <span className={`font-bold text-2xl font-sc truncate ${getRaceTextColor(match.raceB)}`}>
            {match.playerB}
        </span>
        <RaceBadge race={match.raceB} />
      </div>
    </div>
  );
};

// Renamed from Card3Matches to Card3Round to reflect it now renders a single round
const Card3Round: React.FC<Props> = ({ round, index, teamAName, teamBName }) => {
    const isWinnerA = round.scoreA > round.scoreB;
    const isWinnerB = round.scoreB > round.scoreA;

    // Clean names for display
    const displayName = round.name.replace(/^第\d+[局轮]\s*-\s*/, '').replace(/(\d+\/\d+)/, '').trim();
    
    // Guess subtitle based on score logic
    const winningScore = Math.max(round.scoreA, round.scoreB);
    // If score is 5 or more, assume First to 5 (BO9), otherwise default to First to 4 (BO7)
    const subtitle = winningScore >= 5 ? "FIRST TO 5 WINS" : "FIRST TO 4 WINS";

    // Determine winner team name for display
    // Updated: Preserves "队" or "Team" if present in the data
    const winnerTeamDisplay = round.winnerTeam 
        ? round.winnerTeam.toUpperCase() + ' WINS'
        : 'DRAW';

    return (
        <div className="w-full max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-lg flex flex-col mb-8">
            {/* Header */}
            <div className="bg-slate-950 border-b border-slate-700 relative py-5 px-8 min-h-[100px] flex items-center justify-between">
                
                {/* Left: Round Info */}
                <div className="flex flex-col">
                    <div className="flex items-baseline gap-3 mb-1">
                        <span className="text-2xl font-bold text-slate-600 font-exo uppercase tracking-widest">SET {index}</span>
                        <span className="text-3xl font-black text-white font-sc tracking-wide uppercase truncate max-w-[500px]">
                            {round.name.replace(/\[|\]/g, '')}
                        </span>
                    </div>
                    <div className="text-sm text-blue-400 font-bold tracking-widest uppercase pl-1">
                        {subtitle}
                    </div>
                </div>

                {/* Right: Score & Winner */}
                <div className="flex flex-col items-end">
                    <div className="flex items-center font-mono font-bold leading-none mb-2">
                         <span className={`text-7xl ${isWinnerA ? 'text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]' : 'text-slate-600'}`}>{round.scoreA}</span>
                         <span className="text-5xl text-slate-700 mx-3">:</span>
                         <span className={`text-7xl ${isWinnerB ? 'text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]' : 'text-slate-600'}`}>{round.scoreB}</span>
                    </div>
                    {round.winnerTeam && (
                        <div className={`text-lg font-black uppercase tracking-widest ${isWinnerA ? 'text-blue-500 drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]' : 'text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`}>
                            {winnerTeamDisplay}
                        </div>
                    )}
                </div>
            </div>

            {/* Match List */}
            <div className="p-6 bg-slate-900/50">
                {round.matches.map((m, idx) => (
                    <MatchRow key={`${round.name}-${idx}`} match={m} />
                ))}
            </div>
        </div>
    );
};

export default Card3Round;