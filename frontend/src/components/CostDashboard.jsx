import { useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
} from "chart.js";
import { DollarSign, Zap, ChevronUp, ChevronDown } from "lucide-react";
import { calcCost, formatUSD } from "../utils/costTracker";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip);

export default function CostDashboard({ sessions }) {
  const [expanded, setExpanded] = useState(false);

  const totalTokens = sessions.reduce(
    (acc, s) => ({
      input: acc.input + (s.tokens?.input || 0),
      output: acc.output + (s.tokens?.output || 0),
      cache_read: acc.cache_read + (s.tokens?.cache_read || 0),
    }),
    { input: 0, output: 0, cache_read: 0 }
  );

  const totalCost = calcCost(totalTokens);
  const avgLatency =
    sessions.length > 0
      ? sessions.reduce((a, s) => a + s.latency_ms, 0) / sessions.length
      : 0;

  const recentLatencies = sessions.slice(-10);

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 bg-slate-900/95 backdrop-blur border-t
                  border-slate-700/50 transition-all z-50
                  ${expanded ? "h-48" : "h-12"}`}
    >
      {/* Header row */}
      <div
        className="flex items-center gap-6 px-4 h-12 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1">
          <DollarSign size={11} /> Cost & Latency
        </span>

        <div className="flex items-center gap-4 text-xs">
          <span className="text-slate-300">
            Total:{" "}
            <span className="text-green-400 font-mono font-semibold">
              {formatUSD(totalCost)}
            </span>
          </span>
          <span className="text-slate-400">
            Input:{" "}
            <span className="font-mono text-slate-300">
              {totalTokens.input.toLocaleString()}
            </span>
          </span>
          <span className="text-slate-400">
            Cache:{" "}
            <span className="font-mono text-sky-300">
              {totalTokens.cache_read.toLocaleString()}
            </span>
          </span>
          <span className="text-slate-400">
            Output:{" "}
            <span className="font-mono text-violet-300">
              {totalTokens.output.toLocaleString()}
            </span>
          </span>
          <span className="text-slate-400 flex items-center gap-1">
            <Zap size={10} className="text-yellow-400" />
            Avg latency:{" "}
            <span className="font-mono text-yellow-300">
              {avgLatency.toFixed(0)}ms
            </span>
          </span>
          <span className="text-slate-400">
            {sessions.length} queries
          </span>
        </div>

        <div className="ml-auto text-slate-500">
          {expanded ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </div>
      </div>

      {/* Expanded chart */}
      {expanded && (
        <div className="px-4 pb-3 h-36">
          {recentLatencies.length > 0 ? (
            <Bar
              data={{
                labels: recentLatencies.map((_, i) => `Q${sessions.length - recentLatencies.length + i + 1}`),
                datasets: [
                  {
                    label: "Latency (ms)",
                    data: recentLatencies.map((s) => s.latency_ms),
                    backgroundColor: recentLatencies.map((s) =>
                      s.latency_ms < 3000 ? "rgba(52,211,153,0.7)" : "rgba(251,191,36,0.7)"
                    ),
                    borderRadius: 4,
                  },
                ],
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                  tooltip: {
                    callbacks: {
                      label: (ctx) => `${ctx.raw.toFixed(0)}ms`,
                    },
                  },
                },
                scales: {
                  x: {
                    ticks: { color: "#6b7280", font: { size: 10 } },
                    grid: { color: "rgba(255,255,255,0.04)" },
                  },
                  y: {
                    ticks: { color: "#6b7280", font: { size: 10 } },
                    grid: { color: "rgba(255,255,255,0.04)" },
                  },
                },
                animation: false,
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-600 text-sm">
              No queries yet
            </div>
          )}
        </div>
      )}
    </div>
  );
}
