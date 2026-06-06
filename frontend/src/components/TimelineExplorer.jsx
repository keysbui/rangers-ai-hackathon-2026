import { useState } from "react";
import { Clock, ShoppingBag, Music, AlertTriangle, Zap, Sparkles } from "lucide-react";
import { formatSeconds } from "../utils/costTracker";
import AdHighlights from "./AdHighlights";

function EnergyBar({ score }) {
  const pct = Math.round((score || 0) * 100);
  const color =
    score >= 0.7 ? "bg-green-500" : score >= 0.4 ? "bg-yellow-500" : "bg-slate-600";
  return (
    <div className="flex items-center gap-1.5 mt-1">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color} ${score >= 0.7 ? "energy-high" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-slate-500 w-6 text-right">{pct}%</span>
    </div>
  );
}

function SegmentCard({ seg, onSeek, complianceIssues }) {
  const hasIssue = complianceIssues?.some(
    (c) =>
      c.timestamp_start <= seg.timestamp_start &&
      c.timestamp_end >= seg.timestamp_end
  );
  const skus = seg.detected_skus ? seg.detected_skus.split(",").filter(Boolean) : [];

  return (
    <div
      className={`p-3 rounded-lg border cursor-pointer transition-all hover:border-violet-600/50
        ${hasIssue ? "border-red-800/60 bg-red-950/20" : "border-slate-700/50 bg-slate-800/40"}`}
      onClick={() => onSeek(seg.timestamp_start)}
    >
      <div className="flex items-center justify-between mb-1">
        <button
          className="timestamp-chip"
          onClick={(e) => { e.stopPropagation(); onSeek(seg.timestamp_start); }}
        >
          <Clock size={10} />
          {formatSeconds(seg.timestamp_start)}
        </button>
        {hasIssue && (
          <span className="flex items-center gap-1 text-[10px] text-red-400">
            <AlertTriangle size={10} /> Compliance
          </span>
        )}
      </div>

      {seg.transcript && (
        <p className="text-xs text-slate-300 line-clamp-2 mt-1">{seg.transcript}</p>
      )}

      {seg.ocr_text && (
        <p className="text-[10px] text-amber-400/80 mt-1 font-mono truncate">
          {seg.ocr_text}
        </p>
      )}

      {skus.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {skus.slice(0, 3).map((sku, i) => (
            <span
              key={i}
              className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded
                         bg-violet-900/40 text-violet-300 border border-violet-800/30"
            >
              <ShoppingBag size={8} /> {sku.trim()}
            </span>
          ))}
        </div>
      )}

      {seg.audio_event && (
        <div className="flex items-center gap-1 mt-1 text-[10px] text-sky-400/70">
          <Music size={9} /> {seg.audio_event}
        </div>
      )}

      <EnergyBar score={seg.energy_score} />
    </div>
  );
}

export default function TimelineExplorer({ videoId, timeline, complianceIssues, onSeek }) {
  const [activeTab, setActiveTab] = useState("scenes");
  const highEnergy = timeline?.filter((s) => s.energy_score >= 0.7) || [];

  return (
    <div className="h-full min-h-0 flex flex-col bg-slate-900 border-r border-slate-700/50 overflow-hidden">
      {/* Tab Switcher */}
      <div className="flex bg-slate-950/50 p-1 mx-3 mt-3 rounded-lg border border-slate-800">
        <button
          onClick={() => setActiveTab("scenes")}
          className={`flex-1 flex items-center justify-center gap-2 py-1.5 text-[11px] font-medium rounded-md transition-all
            ${activeTab === "scenes" ? "bg-slate-800 text-violet-400 shadow-sm" : "text-slate-500 hover:text-slate-300"}`}
        >
          <Zap size={12} /> Scenes
        </button>
        <button
          onClick={() => setActiveTab("highlights")}
          className={`flex-1 flex items-center justify-center gap-2 py-1.5 text-[11px] font-medium rounded-md transition-all
            ${activeTab === "highlights" ? "bg-slate-800 text-amber-400 shadow-sm" : "text-slate-500 hover:text-slate-300"}`}
        >
          <Sparkles size={12} /> AI Highlights
        </button>
      </div>

      {activeTab === "scenes" ? (
        <>
          <div className="px-4 py-3 border-b border-slate-700/50">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Zap size={14} className="text-violet-400" /> Timeline
            </h2>
            <div className="flex gap-3 mt-2 text-[11px] text-slate-400">
              <span>{timeline?.length || 0} scenes</span>
              <span className="text-green-400">{highEnergy.length} peak moments</span>
              {complianceIssues?.length > 0 && (
                <span className="text-red-400">{complianceIssues.length} issues</span>
              )}
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2">
            {!timeline?.length && (
              <div className="text-center text-slate-500 text-sm mt-8">
                Upload and process a video to see timeline
              </div>
            )}
            {timeline?.map((seg) => (
              <SegmentCard
                key={seg.id}
                seg={seg}
                onSeek={onSeek}
                complianceIssues={complianceIssues}
              />
            ))}
          </div>
        </>
      ) : (
        <AdHighlights videoId={videoId} onSeek={onSeek} />
      )}
    </div>
  );
}
