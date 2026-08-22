import { BattleReportData, Race, Round, Match, PlayerStats, TeamData } from '../types';

export const parseInputText = (text: string): BattleReportData => {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l);
  
  // --- 1. Identify Teams & Rosters First ---
  let teamAName = "Team A";
  let teamBName = "Team B";
  let teamARoster: string[] = [];
  let teamBRoster: string[] = [];
  
  lines.forEach(line => {
    // Regex for [TeamName] Player1 Player2 ...
    // Matches: [神麦队] 神麦 小胖 金正宇 禽兽 永镇
    // Capture full name inside brackets without stripping suffixes
    const teamMatch = line.match(/^\[(.*?)\]\s+(.*)/);
    if (teamMatch) {
      const potentialName = teamMatch[1].trim(); 
      const content = teamMatch[2];

      // Filters to avoid false positives
      if (potentialName.includes('Round') || potentialName.includes('Game') || potentialName.includes('局') || potentialName.includes('Map') || potentialName.includes('轮')) return;
      // Added '负' check to avoid parsing score lines as rosters
      if (content.toLowerCase().includes('vs') || content.includes('胜') || content.includes('负') || /\d/.test(content)) return;

      const players = content.split(/\s+/).filter(x => x && !['Z','P','T'].includes(x));

      if (teamAName === "Team A") {
        teamAName = potentialName;
        teamARoster = players;
      } else {
        teamBName = potentialName;
        teamBRoster = players;
      }
    }
  });

  // --- 2. Extract Prize Config (Winner Takes All Logic) ---
  let perPlayerPrize = 0;
  // Look for "胜者1 Name (₩2,790,000)" or similar
  const prizeLine = lines.find(l => l.includes('胜者1') || l.includes('Winner 1'));
  if (prizeLine) {
    const moneyMatch = prizeLine.match(/[₩￦¥](\d{1,3}(,\d{3})*)/);
    if (moneyMatch) {
      perPlayerPrize = parseInt(moneyMatch[1].replace(/,/g, ''), 10);
    }
  }

  // --- 3. Extract Meta Data ---
  const titleLine = lines[0]?.length > 5 ? lines[0] : "StarCraft Battle Report";
  
  let date = new Date().toISOString().split('T')[0].replace(/-/g, '.');
  const dateRegex = /(\d{4})[.\-](\d{2})[.\-](\d{2})/;
  
  let dateMatch = titleLine.match(dateRegex);
  if (!dateMatch) {
    // Search specific lines or generic text
    const dateLine = lines.find(l => l.match(/\d{4}\.\d{2}\.\d{2}/) || l.includes('日期') || l.includes('Date'));
    if (dateLine) dateMatch = dateLine.match(dateRegex);
  }
  if (dateMatch) {
    date = `${dateMatch[1]}.${dateMatch[2]}.${dateMatch[3]}`;
  }

  // --- 4. Extract Race Mapping ---
  const raceMap: Record<string, Race> = {};
  lines.forEach(line => {
    if (/^[ZPT]\s/.test(line)) {
       const raceChar = line.charAt(0) as Race;
       const players = line.substring(2).split(/\s+/);
       players.forEach(p => raceMap[p] = raceChar);
    }
  });

  // --- 5. Parse Rounds and Matches ---
  const rounds: Round[] = [];
  let currentRound: Round | null = null;
  let isAceMatch = false;
  let aceMatchRound: Round | null = null;

  lines.forEach(line => {
    // Detect Round Header
    if (line.startsWith('[') && (
        line.includes('轮') || 
        line.includes('SET') || 
        line.includes('战') || 
        line.includes('局') ||
        line.toLowerCase().includes('match')
    )) {
       if (currentRound) {
         if (isAceMatch) aceMatchRound = currentRound;
         else rounds.push(currentRound);
       }

       let headerContent = line.match(/^\[(.*?)\]/)?.[1] || "Unknown Round";
       
       // REPLACE "Game/局" with "Round/轮"
       headerContent = headerContent.replace(/局/g, '轮');

       isAceMatch = headerContent.includes('ACE') || headerContent.includes('大将') || headerContent.toLowerCase().includes('super ace');
       
       currentRound = {
         name: headerContent,
         matches: [],
         scoreA: 0,
         scoreB: 0,
         winnerTeam: null,
         aceMode: undefined
       };
       return;
    }

    if (currentRound && isAceMatch) {
        const aceModes: Record<string, string> = {
            '나락전': '大将战（多败选手）',
            '극락전': '大将战（多胜选手）',
            '자연빵': '大将战（随机抽签）'
        };
        const mode = Object.entries(aceModes).find(([korean]) => line.includes(korean));
        if (mode) currentRound.aceMode = mode[1];
    }

    // Detect Match Result
    // Relaxed detection: look for 'vs' and brackets (map name)
    const isMatchLine = line.toLowerCase().includes('vs') && (line.includes('[') || line.includes('【'));
    
    if (isMatchLine && currentRound) {
        // Robust Parsing by splitting 'vs'
        try {
            // Extract Map: [MapName]
            const mapMatch = line.match(/^[\[【](.*?)[\]】]/) || line.match(/^\d+\.\s*[\[【](.*?)[\]】]/);
            const mapName = mapMatch ? mapMatch[1].trim() : "Unknown Map";
            
            // Remove the map part and index (e.g. "1. [Map]") to get the players part
            let playersPart = line.replace(/^(\d+\.\s*)?[\[【](.*?)[\]】]/, '').trim();
            
            // Split by 'vs' (case insensitive)
            const parts = playersPart.split(/vs\.?/i);
            
            if (parts.length === 2) {
                const partA = parts[0].trim();
                const partB = parts[1].trim();

                // Helper to extract Race and Result from a player string like "NameP (胜)"
                const extractInfo = (str: string) => {
                    const resultWin = /[\(（]?(胜|Win|W)[\)）]?/i.test(str);
                    const resultLoss = /[\(（]?(败|Loss|L|负)[\)）]?/i.test(str); // Added 负
                    
                    // Race: look for Z/P/T at end of name or separated
                    // Clean string of result markers first. Added 负
                    let cleanStr = str.replace(/[\(（]?(胜|Win|W|败|Loss|L|负)[\)）]?/gi, '').trim();
                    
                    let race = Race.Unknown;
                    const raceMatch = cleanStr.match(/([ZPT])$/i);
                    if (raceMatch) {
                        race = raceMatch[1].toUpperCase() as Race;
                        cleanStr = cleanStr.slice(0, -1).trim();
                    } else {
                        // Check if race is in map
                         if (raceMap[cleanStr]) race = raceMap[cleanStr];
                    }

                    return { name: cleanStr, race, isWin: resultWin, isLoss: resultLoss };
                };

                const infoA = extractInfo(partA);
                const infoB = extractInfo(partB);

                // Update global race map if found new info
                if (infoA.race !== Race.Unknown) raceMap[infoA.name] = infoA.race;
                if (infoB.race !== Race.Unknown) raceMap[infoB.name] = infoB.race;

                // Determine Winner
                let resultA: 'Win' | 'Loss' = 'Loss';
                if (infoA.isWin) resultA = 'Win';
                else if (infoB.isLoss) resultA = 'Win'; // If B lost, A won
                else if (infoB.isWin) resultA = 'Loss';
                else if (infoA.isLoss) resultA = 'Loss';
                else {
                    // Ambiguous? Default to Win for A if parsed correctly as left side usually denotes winner in some formats,
                    // BUT in this specific log format, winners are marked.
                    // If Ace match and no markers, assume left is winner? 
                    // Let's assume Left is Winner if ambiguous for now, but usually markers exist.
                    resultA = 'Win'; 
                }

                const matchData: Match = {
                    id: currentRound.matches.length + 1,
                    map: mapName,
                    playerA: infoA.name,
                    raceA: infoA.race,
                    resultA: resultA,
                    playerB: infoB.name,
                    raceB: infoB.race,
                    resultB: resultA === 'Win' ? 'Loss' : 'Win',
                    winnerName: resultA === 'Win' ? infoA.name : infoB.name
                };
                currentRound.matches.push(matchData);
            }
        } catch (e) {
            console.warn("Failed to parse match line:", line, e);
        }
    }
    
    // Detect Round Score Summary line (e.g., "TeamA (败) 3 : 4 (胜) TeamB")
    if (currentRound && line.includes(':')) {
        // FIX: Ignore lines that indicate Total/Final score so they don't overwrite round scores
        // These lines usually appear at the very end of the text
        if (line.includes('最终') || line.includes('总') || line.includes('Total') || line.includes('Result') || line.includes('Ace Match')) {
             return;
        }

        const parts = line.split(':');
        if (parts.length === 2) {
             const sA = parseInt(parts[0].replace(/\D/g, ''));
             const sB = parseInt(parts[1].replace(/\D/g, ''));
             
             if (!isNaN(sA) && !isNaN(sB) && sA < 20 && sB < 20) {
                 // Fuzzy match logic for team names
                 const cleanTeamAName = teamAName.replace(/(队|Team)/g, '').trim();
                 const cleanTeamBName = teamBName.replace(/(队|Team)/g, '').trim();

                 // Check for Team A match
                 if (line.includes(teamAName) || (cleanTeamAName.length > 1 && line.includes(cleanTeamAName))) {
                     // Check position relative to colon
                     const idx = line.indexOf(teamAName) > -1 ? line.indexOf(teamAName) : line.indexOf(cleanTeamAName);
                     if (idx < line.indexOf(':')) {
                        currentRound.scoreA = sA;
                        currentRound.scoreB = sB;
                     } else {
                        currentRound.scoreB = sA;
                        currentRound.scoreA = sB;
                     }
                 } 
                 // Check for Team B match
                 else if (line.includes(teamBName) || (cleanTeamBName.length > 1 && line.includes(cleanTeamBName))) {
                      const idx = line.indexOf(teamBName) > -1 ? line.indexOf(teamBName) : line.indexOf(cleanTeamBName);
                      if (idx < line.indexOf(':')) {
                        currentRound.scoreB = sA;
                        currentRound.scoreA = sB;
                      } else {
                        currentRound.scoreA = sA;
                        currentRound.scoreB = sB;
                      }
                 } else {
                     // Default fallback: Assume order matches order of teams if no names found
                     currentRound.scoreA = sA;
                     currentRound.scoreB = sB;
                 }
                 
                 // Determine Round Winner based on score
                 if (currentRound.scoreA > currentRound.scoreB) currentRound.winnerTeam = teamAName;
                 else if (currentRound.scoreB > currentRound.scoreA) currentRound.winnerTeam = teamBName;
             }
        }
    }
  });

  if (currentRound) {
    if (isAceMatch) aceMatchRound = currentRound;
    else rounds.push(currentRound);
  }

  // --- Post-Processing: Calculate Scores if Missing ---
  const allRounds = [...rounds, ...(aceMatchRound ? [aceMatchRound] : [])];
  allRounds.forEach(round => {
      // If scores are 0-0 but matches exist, calculate from match winners
      if (round.scoreA === 0 && round.scoreB === 0 && round.matches.length > 0) {
          let winsA = 0;
          let winsB = 0;
          round.matches.forEach(m => {
              // Check if winner is in Team A roster
              if (teamARoster.includes(m.winnerName) || m.resultA === 'Win') {
                  winsA++;
              } else {
                  winsB++;
              }
          });
          round.scoreA = winsA;
          round.scoreB = winsB;
          
          if (winsA > winsB) round.winnerTeam = teamAName;
          else if (winsB > winsA) round.winnerTeam = teamBName;
      }
  });


  // --- 6. Determine Total Score (Set Score) from Final Line ---
  let totalScoreA = 0;
  let totalScoreB = 0;
  let finalScoreFound = false;
  
  const lastLines = lines.slice(-8); 
  for (const line of lastLines) {
      const scoreMatch = line.match(/(.*?)\s+(\d+)\s*[:]\s*(\d+)/);
      if (scoreMatch) {
          const namePart = scoreMatch[1].trim();
          const cleanName = namePart.replace(/(队|Team)/g, '').trim();
          const cleanTeamAName = teamAName.replace(/(队|Team)/g, '').trim();
          const cleanTeamBName = teamBName.replace(/(队|Team)/g, '').trim();

          const score1 = parseInt(scoreMatch[2]);
          const score2 = parseInt(scoreMatch[3]);

          if (teamAName.includes(cleanName) || cleanName.includes(teamAName) || cleanName === cleanTeamAName) {
              totalScoreA = score1;
              totalScoreB = score2;
              finalScoreFound = true;
          } else if (teamBName.includes(cleanName) || cleanName.includes(teamBName) || cleanName === cleanTeamBName) {
              totalScoreB = score1;
              totalScoreA = score2;
              finalScoreFound = true;
          }
      }
  }

  if (!finalScoreFound) {
      const roundsWonA = rounds.filter(r => r.winnerTeam === teamAName).length + (aceMatchRound?.winnerTeam === teamAName ? 1 : 0);
      const roundsWonB = rounds.filter(r => r.winnerTeam === teamBName).length + (aceMatchRound?.winnerTeam === teamBName ? 1 : 0);
      totalScoreA = roundsWonA;
      totalScoreB = roundsWonB;
  }

  const teamAIsWinner = totalScoreA > totalScoreB;

  // --- 7. Calculate Stats & Prizes ---
  const playerStatsMap = new Map<string, PlayerStats>();

  const initPlayer = (name: string, team: string, isWinnerTeam: boolean) => {
    if (!playerStatsMap.has(name)) {
      playerStatsMap.set(name, {
        name,
        team,
        race: raceMap[name] || Race.Unknown,
        wins: 0,
        losses: 0,
        prizeMoney: isWinnerTeam ? perPlayerPrize : 0 
      });
    }
  };

  teamARoster.forEach(p => initPlayer(p, teamAName, teamAIsWinner));
  teamBRoster.forEach(p => initPlayer(p, teamBName, !teamAIsWinner));

  const allMatches = [...rounds.flatMap(r => r.matches), ...(aceMatchRound ? aceMatchRound.matches : [])];
  
  allMatches.forEach(m => {
      let pA = playerStatsMap.get(m.playerA);
      if (!pA) {
          const isTeamA = teamARoster.includes(m.playerA); 
          playerStatsMap.set(m.playerA, { name: m.playerA, race: m.raceA, team: isTeamA ? teamAName : teamBName, wins: 0, losses: 0, prizeMoney: 0 });
          pA = playerStatsMap.get(m.playerA)!;
      }
      
      let pB = playerStatsMap.get(m.playerB);
      if (!pB) {
          const isTeamB = teamBRoster.includes(m.playerB);
          playerStatsMap.set(m.playerB, { name: m.playerB, race: m.raceB, team: isTeamB ? teamBName : teamAName, wins: 0, losses: 0, prizeMoney: 0 });
          pB = playerStatsMap.get(m.playerB)!;
      }

      if (m.resultA === 'Win') {
          pA.wins++;
          pB.losses++;
      } else {
          pA.losses++;
          pB.wins++;
      }
  });

  const totalPrizePool = Array.from(playerStatsMap.values()).reduce((sum, p) => sum + p.prizeMoney, 0);

  return {
    title: titleLine,
    date,
    teamA: {
      name: teamAName,
      players: teamARoster,
      totalScore: totalScoreA,
      isWinner: teamAIsWinner
    },
    teamB: {
      name: teamBName,
      players: teamBRoster,
      totalScore: totalScoreB,
      isWinner: !teamAIsWinner
    },
    prizePool: totalPrizePool,
    rounds,
    aceMatch: aceMatchRound,
    playerStats: Array.from(playerStatsMap.values())
  };
};
