import { useState } from "react";
import ReactPlayer from "react-player";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from "chart.js";
import { formatSeconds } from "../utils/costTracker";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

function EnergyCurve({ timeline, currentTime }) {
  if (!timeline?.length) return null;

  const labels = timeline.map((s) => formatSeconds(s.timestamp_start));
  const data = timeline.map((s) => s.energy_score * 100);
  const currentIdx = timeline.findIndex(
    (s) => s.timestamp_start <= currentTime && s.timestamp_end >= currentTime
  );

  return (
    <div className="h-16 px-4 pb-2">
      <Line
        data={{
          labels,
          datasets: [
            {
              data,
              fill: true,
              borderColor: "#7c3aed",
              backgroundColor: "rgba(124,58,237,0.15)",
              borderWidth: 1.5,
              pointRadius: labels.map((_, i) => (i === currentIdx ? 4 : 0)),
              pointBackgroundColor: "#a78bfa",
              tension: 0.4,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: {
            x: { display: false },
            y: { display: false, min: 0, max: 100 },
          },
          animation: false,
        }}
      />
    </div>
  );
}

export default function VideoPlayer({ videoSrc, playerRef, timeline, onTimeUpdate }) {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const handleTimeUpdate = () => {
    const t = playerRef.current?.currentTime ?? 0;
    setCurrentTime(t);
    onTimeUpdate?.(t);
  };

  const handleDurationChange = () => {
    setDuration(playerRef.current?.duration ?? 0);
  };

  return (
    <div className="h-full min-h-0 flex flex-col bg-slate-950 overflow-hidden">
      <div className="flex-1 min-h-0 relative">
        {videoSrc ? (
          <ReactPlayer
            ref={playerRef}
            src={videoSrc}
            width="100%"
            height="100%"
            controls
            playsInline
            onTimeUpdate={handleTimeUpdate}
            onDurationChange={handleDurationChange}
            style={{ position: "absolute", inset: 0 }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-slate-600">
            <div className="text-center">
              <div className="text-5xl mb-3">🎬</div>
              <p className="text-sm">Upload a video to get started</p>
            </div>
          </div>
        )}
      </div>

      {/* Energy curve under seekbar */}
      <div className="border-t border-slate-800">
        <div className="px-4 py-1 flex items-center justify-between text-[11px] text-slate-500">
          <span>Energy</span>
          <span>
            {formatSeconds(currentTime)} / {formatSeconds(duration)}
          </span>
        </div>
        <EnergyCurve timeline={timeline} currentTime={currentTime} />
      </div>
    </div>
  );
}
