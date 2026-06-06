import { useState, useRef, useEffect, useCallback } from "react";
import VideoSelector from "./components/VideoSelector";
import TimelineExplorer from "./components/TimelineExplorer";
import VideoPlayer from "./components/VideoPlayer";
import ChatPanel from "./components/ChatPanel";
import CostDashboard from "./components/CostDashboard";
import { api } from "./api/client";

export default function App() {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [compliance, setCompliance] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [videoSrc, setVideoSrc] = useState(null);
  const playerRef = useRef(null);
  // Tracks the currently active video so stale polls cannot overwrite newer state
  const activeIdRef = useRef(null);

  const loadVideoData = useCallback((video) => {
    if (!video) {
      activeIdRef.current = null;
      setTimeline([]);
      setCompliance([]);
      setVideoSrc(null);
      return;
    }

    const id = video.id;
    activeIdRef.current = id;
    setTimeline([]);
    setCompliance([]);
    setVideoSrc(api.streamUrl(id));

    const poll = async () => {
      // Abort if another video was selected meanwhile
      if (activeIdRef.current !== id) return;
      try {
        const v = await api.getVideo(id);
        if (activeIdRef.current !== id) return;
        if (v.status === "done") {
          const tl = await api.getTimeline(id);
          if (activeIdRef.current !== id) return;
          setTimeline(tl);
          api.getCompliance(id)
            .then((c) => {
              if (activeIdRef.current === id) setCompliance(c.issues || []);
            })
            .catch(() => {});
        } else if (v.status !== "error") {
          setTimeout(poll, 3000);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    };

    poll();
  }, []);

  // Reload whenever the selected video id changes
  useEffect(() => {
    loadVideoData(selectedVideo);
  }, [selectedVideo?.id, loadVideoData]);

  const seekTo = useCallback((seconds) => {
    if (playerRef.current) {
      playerRef.current.currentTime = seconds;
      playerRef.current.play?.();
    }
  }, []);

  const handleTokensUsed = useCallback((session) => {
    setSessions((prev) => [...prev, session]);
  }, []);

  const handleSelectVideo = (v) => {
    // If v is null (e.g. video was deleted), just set it
    if (!v) {
      setSelectedVideo(null);
      return;
    }
    // Re-clicking the same video should still refresh its data
    if (selectedVideo?.id === v.id) {
      loadVideoData(v);
    } else {
      setSelectedVideo(v);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden pb-12">
      {/* Top bar */}
      <header className="flex-none bg-slate-900 border-b border-slate-700/50 px-4 py-2
                          flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎬</span>
          <span className="font-semibold text-sm text-slate-100">
            Video Intelligence Engine
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-900/50
                           border border-violet-700/40 text-violet-300">
            BX-T4
          </span>
        </div>
        <span className="text-[11px] text-slate-500 ml-2">
          Powered by Seed-2.0-mini-260428 · BytePlus ModelArk
        </span>
      </header>

      {/* Video selector bar */}
      <VideoSelector selectedId={selectedVideo?.id} onSelect={handleSelectVideo} />

      {/* Main 3-column layout */}
      <div className="flex-1 min-h-0 grid grid-cols-[300px_1fr_320px] grid-rows-[minmax(0,1fr)] overflow-hidden">
        {/* Left: Timeline Explorer */}
        <TimelineExplorer
          videoId={selectedVideo?.id}
          timeline={timeline}
          complianceIssues={compliance}
          onSeek={seekTo}
        />

        {/* Center: Video Player + Energy Curve */}
        <VideoPlayer
          videoSrc={videoSrc}
          playerRef={playerRef}
          timeline={timeline}
          onTimeUpdate={() => {}}
        />

        {/* Right: Chat Q&A */}
        <ChatPanel
          videoId={selectedVideo?.status === "done" ? selectedVideo.id : null}
          onSeek={seekTo}
          onTokensUsed={handleTokensUsed}
        />
      </div>

      {/* Bottom: Cost & Latency Dashboard */}
      <CostDashboard sessions={sessions} />
    </div>
  );
}
