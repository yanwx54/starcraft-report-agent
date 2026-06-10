import React from 'react';
import { BattleReportData, Race } from '../types';
import { BarChart3 } from 'lucide-react';

interface Props {
  data: BattleReportData;
}

const Card2Stats: React.FC<Props> = ({ data }) => {
  const formatMoney = (amount: number) => `₩${amount.toLocaleString()}`;

  const renderPlayerRow = (playerName: string, index: number) => {
    const stats = data.playerStats.find(p => p.name === playerName);
    if (!stats) return null;

    const raceColor = {
        [Race.P]: 'text-yellow-400',
        [Race.T]: 'text-blue-400',
        [Race.Z]: 'text-purple-400',
        [Race.Unknown]: 'text-white'
    }[stats.race];

    return (
      <tr key={playerName} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
        <td className={`py-5 px-5 font-bold text-xl ${raceColor}`}>{stats.name}</td>
        <td className={`py-5 px-5 font-bold text-xl ${raceColor}`}>{stats.race}</td>
        <td className="py-5 px-5 text-slate-300 font-mono text-lg">{stats.wins} - {stats.losses}</td>
        <td className={`py-5 px-5 font-bold font-mono text-right text-lg ${stats.prizeMoney > 0 ? 'text-green-400' : 'text-slate-500'}`}>
          {formatMoney(stats.prizeMoney)}
        </td>
      </tr>
    );
  };

  return (
    <div className="w-full max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-2xl mb-8">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-5 bg-slate-800 border-b border-slate-700">
        <BarChart3 className="text-yellow-500" size={28} />
        <h2 className="text-2xl font-bold text-white font-sc tracking-wide">选手表现 & 奖金</h2>
        <span className="ml-auto text-base text-slate-500 tracking-widest">STATISTICS</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2">
        {/* Team A Column */}
        <div className="border-r border-slate-700">
          <div className="bg-blue-900/20 px-6 py-4 border-b border-blue-500/20 flex justify-between items-center">
            <h3 className="text-blue-400 font-bold uppercase tracking-wider text-lg">{data.teamA.name}</h3>
            <span className="text-xs text-blue-500/70 font-bold">WINNERS</span>
          </div>
          <table className="w-full text-left">
            <thead className="bg-slate-950/30 text-base uppercase text-slate-500 font-semibold tracking-wider">
              <tr>
                <th className="py-3 px-5">Player</th>
                <th className="py-3 px-5">Race</th>
                <th className="py-3 px-5">W-L</th>
                <th className="py-3 px-5 text-right">Prize</th>
              </tr>
            </thead>
            <tbody>
              {data.teamA.players.map((p, i) => renderPlayerRow(p, i))}
            </tbody>
          </table>
        </div>

        {/* Team B Column */}
        <div>
          <div className="bg-red-900/20 px-6 py-4 border-b border-red-500/20 flex justify-between items-center">
            <h3 className="text-red-400 font-bold uppercase tracking-wider text-lg">{data.teamB.name}</h3>
            <span className="text-xs text-red-500/70 font-bold">CHALLENGERS</span>
          </div>
          <table className="w-full text-left">
            <thead className="bg-slate-950/30 text-base uppercase text-slate-500 font-semibold tracking-wider">
              <tr>
                <th className="py-3 px-5">Player</th>
                <th className="py-3 px-5">Race</th>
                <th className="py-3 px-5">W-L</th>
                <th className="py-3 px-5 text-right">Prize</th>
              </tr>
            </thead>
            <tbody>
              {data.teamB.players.map((p, i) => renderPlayerRow(p, i))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Card2Stats;