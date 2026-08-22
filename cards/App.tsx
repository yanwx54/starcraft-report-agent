import React, { useState, useEffect } from 'react';
import { parseInputText } from './utils/parser';
import { BattleReportData } from './types';
import Card1Summary from './components/Card1Summary';
import Card2Stats from './components/Card2Stats';
import Card3Round from './components/Card3Matches'; // Reusing this file as the single round card
import Card4Ace from './components/Card4Ace';
import { FileText, Play, ChevronDown, ChevronUp, Download, Images } from 'lucide-react';

// Default example text
const DEFAULT_TEXT = `2025年11月21日 (周五) 星际争霸 5:5 Major 职业联赛
42 Pabo 0 236 11.22 03:05
日期 2025-11-21
胜者1 石头 (₩2,790,000)
胜者2 光哥 (₩2,790,000)
胜者3 小零 (₩2,790,000)
胜者4 迷你 (₩2,790,000)
胜者5 夏普 (₩2,790,000)
败者 神麦 金正宇 小胖 禽兽 永镇
总计 27,900个

- 队伍选择: 神麦/石头 分队后抽签

- 第1局: 7/4 职业联赛

- 第2局: 9/5 胜者联赛

- Super Ace: 大将战（多败选手）、大将战（多胜选手）或大将战（随机抽签）

(极乐/奈落: 净胜分>多胜优先)

Z 小零 金正宇 小胖
P 禽兽 迷你 石头
T 神麦 永镇 光哥 夏普

[神麦队] 神麦 小胖 金正宇 禽兽 永镇
[石头队] 石头 光哥 小零 迷你 夏普

[第1局 - 7/4 职业联赛]

1. [统治者] 永镇T (胜) vs (败) 小零Z
2. [大都会] 小胖Z (胜) vs (败) 夏普T
3. [北极星] 金正宇Z (胜) vs (败) 迷你P
4. [局外人] 神麦T (败) vs (胜) 光哥T
5. [石蕊] 禽兽P (败) vs (胜) 石头P
6. [海峡] 永镇T (败) vs (胜) 夏普T
7. [镭龙] 金正宇Z (败) vs (胜) 小零Z

神麦队 (败) 3 : 4 (胜) 石头队

[第2局 - 9/5 胜者联赛]

1. [北极星] 永镇T (败) vs (胜) 夏普T
2. [大都会] 金正宇Z (败) vs (胜) 夏普T
3. [镭龙] 禽兽P (胜) vs (败) 夏普T
4. [局外人] 禽兽P (胜) vs (败) 迷你P
5. [统治者] 禽兽P (败) vs (胜) 小零Z
6. [石蕊] 神麦T (败) vs (胜) 小零Z
7. [局外人] 小胖Z (胜) vs (败) 小零Z
8. [大都会] 小胖Z (胜) vs (败) 石头P
9. [统治者] 小胖Z (败) vs (胜) 光哥T

神麦队 (败) 4 : 5 (胜) 石头队

[第3局 - Super Ace Match]
[大都会] 石头P (胜) vs (败) 小零Z

最终结果
石头队 2 : 0 胜`;

const App: React.FC = () => {
  const [inputText, setInputText] = useState<string>(DEFAULT_TEXT);
  const [data, setData] = useState<BattleReportData | null>(null);
  const [showInput, setShowInput] = useState<boolean>(true);
  const [isDownloading, setIsDownloading] = useState(false);

  // Initialize data on load
  useEffect(() => {
    handleParse();
  }, []);

  const handleParse = () => {
    try {
      const parsedData = parseInputText(inputText);
      setData(parsedData);
      // Removed auto-hide logic to keep input visible unless manually toggled
    } catch (e) {
      console.error("Parse error", e);
      alert("Error parsing text. Please check the format.");
    }
  };

  const generateImage = async (elementId: string, fileName: string) => {
    const element = document.getElementById(elementId);
    if (!element || !(window as any).html2canvas) return false;

    try {
      const canvas = await (window as any).html2canvas(element, {
        backgroundColor: '#0a0e17', // Match the body background
        scale: 2, // High resolution
        useCORS: true, // Allow cross-origin images
        logging: false,
      });
      
      const link = document.createElement('a');
      link.download = `${fileName}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
      return true;
    } catch (err) {
      console.error(`Failed to generate ${fileName}:`, err);
      return false;
    }
  };

  const handleDownloadFull = async () => {
    setIsDownloading(true);
    await generateImage('report-content', `battle-report-full-${new Date().toISOString().slice(0,10)}`);
    setIsDownloading(false);
  };

  const handleDownloadSplit = async () => {
    if (!data) return;
    setIsDownloading(true);
    
    try {
        // 1. Summary
        if (document.getElementById('report-card-summary')) {
            await generateImage('report-card-summary', `1_Summary`);
            await new Promise(r => setTimeout(r, 500));
        }

        // 2. Stats
        if (document.getElementById('report-card-stats')) {
            await generateImage('report-card-stats', `2_Stats`);
            await new Promise(r => setTimeout(r, 500));
        }

        // 3. Rounds (Dynamic)
        for (let i = 0; i < data.rounds.length; i++) {
            const id = `report-card-round-${i}`;
            if (document.getElementById(id)) {
                await generateImage(id, `3_Round_${i + 1}`);
                await new Promise(r => setTimeout(r, 500));
            }
        }

        // 4. Ace
        if (document.getElementById('report-card-ace')) {
            await generateImage('report-card-ace', `4_AceMatch`);
        }

    } catch (e) {
        console.error("Split download error", e);
    } finally {
        setIsDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] text-slate-200 pb-20">
      
      {/* Navbar */}
      <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(37,99,235,0.5)]">
               <FileText className="text-white" size={20} />
            </div>
            <span className="font-bold text-lg font-sc text-white hidden md:inline">SC:Remastered Battle Report</span>
            <span className="font-bold text-lg font-sc text-white md:hidden">SC Report</span>
          </div>
          
          <div className="flex items-center gap-2 md:gap-4">
             {data && (
                <>
                    <button 
                      onClick={handleDownloadSplit}
                      disabled={isDownloading}
                      className="flex items-center gap-2 text-sm bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded transition-colors disabled:opacity-50"
                      title="Download Separate Images"
                    >
                      <Images size={16} />
                      <span className="hidden sm:inline">{isDownloading ? "Saving..." : "Split Images"}</span>
                    </button>
                    
                    <button 
                      onClick={handleDownloadFull}
                      disabled={isDownloading}
                      className="flex items-center gap-2 text-sm bg-green-600 hover:bg-green-500 text-white px-3 py-1.5 rounded transition-colors disabled:opacity-50"
                      title="Download Full Report"
                    >
                      <Download size={16} />
                      <span className="hidden sm:inline">{isDownloading ? "Saving..." : "Full Image"}</span>
                    </button>
                </>
             )}

             <button 
              onClick={() => setShowInput(!showInput)}
              className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded transition-colors ${showInput ? 'text-slate-400 hover:text-white' : 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg'}`}
             >
               <span className="hidden sm:inline">{showInput ? "Hide Editor" : "Edit Data"}</span>
               {showInput ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
             </button>
          </div>
        </div>
      </nav>

      {/* Input Section */}
      {showInput && (
        <div className="max-w-4xl mx-auto p-4 animate-in slide-in-from-top-4 duration-300">
          <div className="bg-slate-800 rounded-lg p-4 shadow-xl border border-slate-700">
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Paste Match Text Data
            </label>
            <textarea
              className="w-full h-64 bg-slate-950 border border-slate-700 rounded-md p-4 font-mono text-sm text-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste the battle report text here..."
            />
            <div className="mt-4 flex justify-end">
              <button
                onClick={handleParse}
                className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-6 rounded-md flex items-center gap-2 transition-all shadow-[0_0_20px_rgba(37,99,235,0.4)] hover:shadow-[0_0_30px_rgba(37,99,235,0.6)]"
              >
                <Play size={18} fill="currentColor" />
                Generate Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        {data ? (
          // Wrapped with ID for html2canvas
          <div id="report-content" className="space-y-8 animate-in fade-in duration-700 w-full max-w-4xl mx-auto">
            
            {/* Card 1: Summary */}
            <div id="report-card-summary" className="w-full">
                <Card1Summary data={data} />
            </div>

            {/* Card 2: Stats */}
            <div id="report-card-stats" className="w-full">
                <Card2Stats data={data} />
            </div>

            {/* Card 3: Rounds - Rendered Individually */}
            {data.rounds.map((round, idx) => (
                <div key={idx} id={`report-card-round-${idx}`} className="w-full">
                    <Card3Round round={round} index={idx + 1} teamAName={data.teamA.name} teamBName={data.teamB.name} />
                </div>
            ))}

            {/* Card 4: Ace Match */}
            {data.aceMatch && (
                <div id="report-card-ace" className="w-full">
                    <Card4Ace data={data} />
                </div>
            )}
          </div>
        ) : (
          <div className="text-center py-20 opacity-50">
            <p>Enter data to generate visualization.</p>
          </div>
        )}
      </main>

      <footer className="mt-12 text-center text-slate-600 text-sm pb-8">
        StarCraft Battle Report Generator • Built with React & Tailwind
      </footer>
    </div>
  );
};

export default App;
