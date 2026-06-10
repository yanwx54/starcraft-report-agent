import React from 'react';
import { BattleReportData, Race } from '../types';
import { Trophy } from 'lucide-react';

interface Props {
  data: BattleReportData;
}

const Card4Ace: React.FC<Props> = ({ data }) => {
  const round = data.aceMatch;
  if (!round || round.matches.length === 0) return null;

  const match = round.matches[0];
  const isWinnerA = match.resultA === 'Win';
  
  // Logic to determine Ace Winner Team Name
  // If playerA won, look for playerA's team. If player A is in teamA roster, it's TeamA, etc.
  // A simple heuristic: if isWinnerA, calculate which team Player A belongs to.
  // Data structure has `teamA.players` and `teamB.players`.
  const winnerTeamName = isWinnerA 
      ? (data.teamA.players.includes(match.playerA) ? data.teamA.name : data.teamB.name)
      : (data.teamB.players.includes(match.playerB) ? data.teamB.name : data.teamA.name);

  // Updated: Preserves "队" or "Team" if present in the data
  const displayWinnerTeam = winnerTeamName.toUpperCase();
  
  // Helper for Race colors in the circle border
  const getRaceColor = (race: Race) => {
    switch(race) {
        case Race.P: return 'border-yellow-400 text-yellow-400';
        case Race.T: return 'border-blue-400 text-blue-400';
        case Race.Z: return 'border-purple-400 text-purple-400';
        default: return 'border-white text-white';
    }
  };

  const getRaceLetter = (race: Race) => {
      return race === Race.Unknown ? '?' : race;
  };

  return (
    <div className="w-full max-w-4xl mx-auto bg-[#1a1a1a] border border-yellow-500 rounded-xl overflow-hidden shadow-2xl mb-8 relative">
       
       {/* Top Header */}
       <div className="text-center pt-8 pb-4 relative z-10">
            <div className="flex items-center justify-center gap-3 mb-2">
                <Trophy size={20} className="text-yellow-500" />
                <h2 className="text-3xl font-black text-white uppercase tracking-widest font-exo">SET 3: SUPER ACE MATCH</h2>
                <Trophy size={20} className="text-yellow-500" />
            </div>
            <div className="text-slate-400 italic font-medium text-sm">"Winner Takes All"</div>
            
            {/* Top Right Winner Badge */}
            <div className="absolute top-6 right-8 flex flex-col items-end">
                <div className="text-yellow-500 font-bold uppercase tracking-widest text-sm">
                    {displayWinnerTeam} WINS
                </div>
            </div>
       </div>

       {/* Main Content Area */}
       <div className="relative h-80 w-full flex items-center justify-center z-10">
          
          {/* Player A (Left) */}
          <div className="flex flex-col items-center justify-center w-1/3">
             {/* Circle Avatar Placeholder */}
             <div className={`relative w-32 h-32 rounded-full border-4 flex items-center justify-center bg-black/50 mb-4 shadow-[0_0_20px_rgba(0,0,0,0.5)] relative ${getRaceColor(match.raceA)} ${isWinnerA ? 'shadow-[0_0_30px_rgba(234,179,8,0.4)]' : ''}`}>
                 <span className="text-6xl font-black">{getRaceLetter(match.raceA)}</span>
                 {isWinnerA && (
                     <div className="absolute -bottom-3 bg-yellow-500 text-black text-xs font-bold px-3 py-0.5 rounded uppercase shadow-lg z-20">Winner</div>
                 )}
             </div>
             <div className="text-3xl font-bold text-white font-sc mb-1">{match.playerA}</div>
             <div className="text-yellow-500/80 text-sm font-bold uppercase tracking-wider">{data.teamA.name.replace(/(队|Team)/g, '')} Team</div>
          </div>

          {/* Center VS */}
          <div className="flex flex-col items-center justify-center w-1/4">
             <div className="text-7xl font-black text-white italic tracking-tighter drop-shadow-lg mb-2">VS</div>
             <div className="bg-blue-900/40 border border-blue-500/50 px-4 py-1 rounded text-blue-300 text-sm font-bold uppercase tracking-wider">
                 Map: {match.map}
             </div>
          </div>

          {/* Player B (Right) */}
          <div className="flex flex-col items-center justify-center w-1/3">
             <div className={`relative w-32 h-32 rounded-full border-4 flex items-center justify-center bg-black/50 mb-4 shadow-[0_0_20px_rgba(0,0,0,0.5)] relative ${getRaceColor(match.raceB)} ${!isWinnerA ? 'shadow-[0_0_30px_rgba(234,179,8,0.4)]' : ''}`}>
                 <span className="text-6xl font-black">{getRaceLetter(match.raceB)}</span>
                 {!isWinnerA && (
                     <div className="absolute -bottom-3 bg-yellow-500 text-black text-xs font-bold px-3 py-0.5 rounded uppercase shadow-lg z-20">Winner</div>
                 )}
             </div>
             <div className="text-3xl font-bold text-white font-sc mb-1">{match.playerB}</div>
             <div className="text-slate-500 text-sm font-bold uppercase tracking-wider">{data.teamB.name.replace(/(队|Team)/g, '')} Team</div>
          </div>

       </div>

       {/* Corner Accents */}
       <div className="absolute top-0 left-0 w-full h-full border-2 border-yellow-500/20 rounded-xl pointer-events-none z-20"></div>
    </div>
  );
};

export default Card4Ace;