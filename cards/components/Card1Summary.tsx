import React from 'react';
import { BattleReportData, Race } from '../types';
import { PLAYER_ID_MAP } from '../utils/mappings';

interface Props {
  data: BattleReportData;
}

const Card1Summary: React.FC<Props> = ({ data }) => {
  const formatMoney = (amount: number) => `₩${amount.toLocaleString()}`;

  // Helper to find player race from stats
  const getRace = (name: string) => data.playerStats.find(p => p.name === name)?.race || Race.Unknown;

  // Calculate per-player prize for display if available
  const winnerPrizePerPlayer = data.teamA.isWinner 
    ? (data.playerStats.find(p => p.team === data.teamA.name)?.prizeMoney || 0)
    : (data.playerStats.find(p => p.team === data.teamB.name)?.prizeMoney || 0);

  const renderRoster = (players: string[]) => {
      return players.map(player => {
          const race = getRace(player);
          const englishId = PLAYER_ID_MAP[player];
          
          const raceColor = {
            [Race.P]: 'text-yellow-400',
            [Race.T]: 'text-blue-400',
            [Race.Z]: 'text-purple-400',
            [Race.Unknown]: 'text-slate-300'
          }[race];

          const boxStyle = {
            [Race.P]: 'border-yellow-500 text-yellow-400 bg-yellow-950/30',
            [Race.T]: 'border-blue-500 text-blue-400 bg-blue-950/30',
            [Race.Z]: 'border-purple-500 text-purple-400 bg-purple-950/30',
            [Race.Unknown]: 'border-slate-500 text-slate-400 bg-slate-950/30'
          }[race];
          
          return (
              <div key={player} className="flex items-center mb-3 last:mb-0">
                  <div className={`w-6 h-6 md:w-7 md:h-7 rounded border flex items-center justify-center text-xs md:text-sm font-bold font-exo mr-3 flex-shrink-0 shadow-sm ${boxStyle}`}>
                      {race}
                  </div>
                  <div className={`font-sc font-bold text-base md:text-xl tracking-wide truncate flex items-baseline gap-2 ${raceColor} drop-shadow-md`}>
                      <span>{player}</span>
                      {englishId && <span className="font-exo font-bold opacity-90">{englishId}</span>}
                  </div>
              </div>
          );
      });
  };

  return (
    <div className="w-full max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-2xl relative">
      {/* Background Ambience */}
      <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(to_bottom,#0f172a_0%,#020617_100%)] z-0"></div>
      <div className="absolute top-0 left-0 w-full h-32 bg-blue-900/10 blur-3xl z-0 pointer-events-none"></div>

      {/* Main Content Container */}
      <div className="relative z-10 flex flex-col items-center p-6 md:p-8">
        
        {/* Top Header Section */}
        <div className="w-full text-center mb-6">
            <h1 className="text-3xl md:text-5xl font-black text-white uppercase italic tracking-wider font-sc drop-shadow-lg">
                {data.title}
            </h1>
        </div>

        {/* Main Matchup Row */}
        <div className="flex flex-col md:flex-row w-full items-stretch justify-center gap-4">
            
            {/* Team A Box (Blue Theme) */}
            <div className="flex-1 bg-blue-900/10 border border-blue-500/30 rounded-lg relative overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-4 border-b border-blue-500/20 flex justify-between items-center bg-blue-950/40">
                    <h2 className="text-xl md:text-3xl font-bold text-blue-100 uppercase font-sc truncate pr-2">{data.teamA.name}</h2>
                    {data.teamA.isWinner ? (
                        <span className="bg-blue-600 text-white text-xs md:text-sm font-bold px-3 py-1 rounded shadow-[0_0_10px_rgba(37,99,235,0.8)] uppercase">WINNER</span>
                    ) : (
                        <span className="bg-slate-700 text-slate-300 text-xs md:text-sm font-bold px-3 py-1 rounded uppercase">LOSER</span>
                    )}
                </div>
                {/* Roster List */}
                <div className="p-4 md:p-5 flex-grow bg-gradient-to-b from-transparent to-blue-950/20 flex flex-col justify-center">
                    {renderRoster(data.teamA.players)}
                </div>
            </div>

            {/* Center Score & Info */}
            <div className="flex flex-col items-center justify-center px-4 md:px-6 py-2 min-w-[200px]">
                
                {/* Total Pot (Moved to Top) */}
                <div className="mb-4 text-center">
                    <div className="text-slate-500 font-bold text-[10px] md:text-xs uppercase tracking-[0.2em] mb-1">Total Prize Pool</div>
                    <div className="text-green-400 font-mono font-bold text-2xl md:text-3xl break-words leading-none drop-shadow-sm">
                        {formatMoney(data.prizePool)}
                    </div>
                </div>

                {/* Score */}
                <div className="text-7xl md:text-8xl font-black text-white font-mono tracking-tighter leading-none flex items-center gap-2 drop-shadow-[0_0_20px_rgba(255,255,255,0.15)] my-2">
                    <span>{data.teamA.totalScore}</span>
                    <span className="text-slate-600 text-5xl">:</span>
                    <span>{data.teamB.totalScore}</span>
                </div>
                <div className="text-slate-600 font-bold text-[10px] tracking-[0.4em] uppercase mb-6">Final Score</div>
                
                {/* Winner Prize (Moved to Bottom) */}
                 <div className="mt-2 text-center border border-yellow-500/30 bg-yellow-500/5 rounded px-4 py-2 w-full">
                    <div className="text-yellow-600 font-bold text-[10px] md:text-xs uppercase tracking-wider mb-0.5">Winner Prize</div>
                    <div className="text-yellow-400 font-mono font-bold text-lg md:text-xl">
                        {formatMoney(winnerPrizePerPlayer)} <span className="text-yellow-600/70 text-xs font-sans font-normal">/ Player</span>
                    </div>
                </div>
            </div>

            {/* Team B Box (Red Theme) */}
            <div className="flex-1 bg-red-900/10 border border-red-500/30 rounded-lg relative overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-4 border-b border-red-500/20 flex justify-between items-center bg-red-950/40">
                    <h2 className="text-xl md:text-3xl font-bold text-red-100 uppercase font-sc truncate pr-2">{data.teamB.name}</h2>
                    {data.teamB.isWinner ? (
                        <span className="bg-red-600 text-white text-xs md:text-sm font-bold px-3 py-1 rounded shadow-[0_0_10px_rgba(220,38,38,0.8)] uppercase">WINNER</span>
                    ) : (
                         <span className="bg-slate-700 text-slate-300 text-xs md:text-sm font-bold px-3 py-1 rounded uppercase">LOSER</span>
                    )}
                </div>
                {/* Roster List */}
                <div className="p-4 md:p-5 flex-grow bg-gradient-to-b from-transparent to-red-950/20 flex flex-col justify-center">
                    {renderRoster(data.teamB.players)}
                </div>
            </div>

        </div>

      </div>
    </div>
  );
};

export default Card1Summary;