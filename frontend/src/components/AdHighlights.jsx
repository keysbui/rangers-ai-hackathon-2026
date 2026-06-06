import { useState, useEffect, useCallback } from 'react';
import { Sparkles, Play, Quote, TrendingUp, RefreshCw, Download, Scissors } from 'lucide-react';
import { api } from '../api/client';
import { formatSeconds } from '../utils/costTracker';

export default function AdHighlights({ videoId, onSeek }) {
  const [highlights, setHighlights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trends] = useState('');

  const fetchHighlights = useCallback(async (force = false) => {
    if (!videoId) return;
    setLoading(true);
    try {
      const data = await api.getHighlights(videoId, trends, force);
      setHighlights(data.highlights || []);
    } catch (err) {
      console.error('Failed to fetch highlights:', err);
    } finally {
      setLoading(false);
    }
  }, [videoId, trends]);

  useEffect(() => {
    fetchHighlights(false);
  }, [fetchHighlights]);

  const handleDownload = (e, index) => {
    e.stopPropagation();
    const url = api.downloadHighlightUrl(videoId, index);
    window.open(url, '_blank');
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-slate-900/50">
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between bg-slate-900">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Sparkles size={14} className="text-amber-400" /> Ad Highlights
        </h2>
        <button 
          onClick={() => fetchHighlights(true)}
          disabled={loading}
          className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 transition-colors"
          title="Refresh highlights"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Trend Info */}
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg p-3">
          <div className="flex items-center gap-2 text-violet-400 text-[11px] font-bold uppercase tracking-wider mb-1">
            <TrendingUp size={12} /> Market Trends Applied
          </div>
          <p className="text-[12px] text-slate-300 leading-relaxed italic">
            "Targeting high-energy viral moments, flash sales, and authentic product demos common in SE Asian e-commerce."
          </p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <RefreshCw size={24} className="animate-spin mb-3 opacity-20" />
            <p className="text-sm">Seed-2.0-mini is analyzing viral potential...</p>
          </div>
        ) : !videoId ? (
          <div className="text-center py-12 text-slate-500">
            <p className="text-sm">Select a video to see ad highlights.</p>
          </div>
        ) : highlights.length > 0 ? (
          highlights.map((h, idx) => (
            <div 
              key={idx}
              className="group bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden hover:border-amber-500/50 transition-all duration-300 cursor-pointer"
              onClick={() => onSeek(h.timestamp)}
            >
              <div className="relative aspect-video bg-slate-900">
                <img 
                  src={h.thumbnail_url} 
                  alt="Highlight"
                  className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                />
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                  <Play size={32} className="text-white fill-white" />
                </div>
                <div className="absolute top-2 left-2 flex gap-1">
                  <div className="bg-amber-500 text-black text-[10px] font-bold px-1.5 py-0.5 rounded shadow-lg">
                    #HIGHLIGHT {idx + 1}
                  </div>
                  {h.viral_score && (
                    <div className="bg-violet-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-lg flex items-center gap-0.5">
                      <TrendingUp size={8} /> {Math.round(h.viral_score)}
                    </div>
                  )}
                </div>
                <div className="absolute bottom-2 right-2 flex gap-1">
                  <div className="bg-black/60 backdrop-blur-md text-white text-[10px] px-1.5 py-0.5 rounded border border-white/10 flex items-center gap-1">
                    <Scissors size={8} className="text-violet-400" />
                    {formatSeconds(h.refined_end - h.refined_start)}
                  </div>
                  <div className="bg-black/60 backdrop-blur-md text-white text-[10px] px-1.5 py-0.5 rounded border border-white/10">
                    {formatSeconds(h.timestamp)}
                  </div>
                </div>
              </div>
              
              <div className="p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 flex-1">
                    <div className="mt-1 p-1 bg-violet-500/20 rounded text-violet-400">
                      <TrendingUp size={12} />
                    </div>
                    <p className="text-[12px] text-slate-300 leading-tight">
                      {h.reason}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDownload(e, idx)}
                    className="p-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg transition-colors shadow-lg shadow-violet-900/20 shrink-0"
                    title="Download refined clip"
                  >
                    <Download size={14} />
                  </button>
                </div>
                
                <div className="bg-slate-900/60 rounded-lg p-2 border border-slate-700/30">
                  <div className="flex gap-1.5 text-amber-400 mb-1">
                    <Quote size={10} />
                    <span className="text-[9px] font-bold uppercase tracking-widest opacity-70">Suggested Ad Copy</span>
                  </div>
                  <p className="text-[13px] text-white font-medium leading-snug">
                    {h.ad_copy}
                  </p>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12 text-slate-500">
            <p className="text-sm">No highlights found for the current trends.</p>
          </div>
        )}
      </div>
    </div>
  );
}
