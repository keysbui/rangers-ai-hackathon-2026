import { useState, useRef, useEffect, useCallback } from "react";
import VideoSelector from "./components/VideoSelector";
import TimelineExplorer from "./components/TimelineExplorer";
import VideoPlayer from "./components/VideoPlayer";
import ChatPanel from "./components/ChatPanel";
import CostDashboard from "./components/CostDashboard";
import { api } from "./api/client";

const TIMELINE_WIDTH = 300;
const DIVIDER_WIDTH = 10;
const MIN_VIDEO_WIDTH = 480;
const MIN_CHAT_WIDTH = 280;
const DEFAULT_CHAT_WIDTH = 320;
const CHAT_RESIZE_STEP = 24;

export default function App() {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [compliance, setCompliance] = useState([]);
  const [policyAudit, setPolicyAudit] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [videoSrc, setVideoSrc] = useState(null);
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH);
  const playerRef = useRef(null);
  const mainLayoutRef = useRef(null);
  // Tracks the currently active video so stale polls cannot overwrite newer state
  const activeIdRef = useRef(null);

  const clampChatWidth = useCallback((width) => {
    const layout = mainLayoutRef.current;
    if (!layout) return Math.max(MIN_CHAT_WIDTH, width);

    const maxChatWidth = Math.max(
      MIN_CHAT_WIDTH,
      layout.clientWidth - TIMELINE_WIDTH - DIVIDER_WIDTH - MIN_VIDEO_WIDTH
    );

    return Math.min(Math.max(width, MIN_CHAT_WIDTH), maxChatWidth);
  }, []);

  const resizeChatFromClientX = useCallback((clientX) => {
    const layout = mainLayoutRef.current;
    if (!layout) return;

    const bounds = layout.getBoundingClientRect();
    setChatWidth(clampChatWidth(bounds.right - clientX));
  }, [clampChatWidth]);

  const handleResizePointerDown = useCallback((event) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    resizeChatFromClientX(event.clientX);

    const handlePointerMove = (moveEvent) => {
      resizeChatFromClientX(moveEvent.clientX);
    };

    const stopResize = () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResize);
      window.removeEventListener("pointercancel", stopResize);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResize);
    window.addEventListener("pointercancel", stopResize);
  }, [resizeChatFromClientX]);

  const handleResizeKeyDown = useCallback((event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight" && event.key !== "Home") {
      return;
    }

    event.preventDefault();
    setChatWidth((width) => {
      if (event.key === "Home") return clampChatWidth(DEFAULT_CHAT_WIDTH);
      const direction = event.key === "ArrowLeft" ? CHAT_RESIZE_STEP : -CHAT_RESIZE_STEP;
      return clampChatWidth(width + direction);
    });
  }, [clampChatWidth]);

  useEffect(() => {
    const handleWindowResize = () => {
      setChatWidth((width) => clampChatWidth(width));
    };

    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
  }, [clampChatWidth]);

  const loadVideoData = useCallback((video) => {
    if (!video) {
      activeIdRef.current = null;
      setTimeline([]);
      setCompliance([]);
      setPolicyAudit([]);
      setVideoSrc(null);
      return;
    }

    const id = video.id;
    activeIdRef.current = id;
    setTimeline([]);
    setCompliance([]);
    setPolicyAudit([]);
    setVideoSrc(api.streamUrl(id));

    const poll = async () => {
      // Abort if another video was selected meanwhile
      if (activeIdRef.current !== id) return;
      try {
        const v = await api.getVideo(id);
        if (activeIdRef.current !== id) return;
        setSelectedVideo((current) => (current?.id === id ? v : current));
        if (v.status === "done") {
          const tl = await api.getTimeline(id);
          if (activeIdRef.current !== id) return;
          setTimeline(tl);
          api.getCompliance(id)
            .then((c) => {
              if (activeIdRef.current === id) setCompliance(c.issues || []);
            })
            .catch(() => {});
          api.getPolicyAudit(id, {
            mode: "auto",
            limit: 200,
            min_confidence: 0.5,
            max_model_calls: 50,
          })
            .then((r) => {
              if (activeIdRef.current === id) setPolicyAudit(r.segments || []);
            })
            .catch(() => {});
        } else if (v.status !== "error") {
          setTimeout(poll, 3000);
        }
      } catch {
        // Polling is best-effort; the next user action can refresh video data.
      }
    };

    poll();
  }, []);

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
      loadVideoData(null);
      return;
    }
    // Re-clicking the same video should still refresh its data
    if (selectedVideo?.id === v.id) {
      loadVideoData(v);
    } else {
      setSelectedVideo(v);
      loadVideoData(v);
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
      <div
        ref={mainLayoutRef}
        className="flex-1 min-h-0 grid grid-rows-[minmax(0,1fr)] overflow-hidden"
        style={{
          gridTemplateColumns: `${TIMELINE_WIDTH}px minmax(${MIN_VIDEO_WIDTH}px, 1fr) ${DIVIDER_WIDTH}px minmax(${MIN_CHAT_WIDTH}px, ${chatWidth}px)`,
        }}
      >
        {/* Left: Timeline Explorer */}
        <TimelineExplorer
          videoId={selectedVideo?.id}
          timeline={timeline}
          complianceIssues={compliance}
          policyAuditSegments={policyAudit}
          onSeek={seekTo}
        />

        {/* Center: Video Player + Energy Curve */}
        <VideoPlayer
          videoSrc={videoSrc}
          playerRef={playerRef}
          timeline={timeline}
          onTimeUpdate={() => {}}
        />

        <div
          role="separator"
          aria-label="Resize video and chat panels"
          aria-orientation="vertical"
          tabIndex={0}
          onPointerDown={handleResizePointerDown}
          onDoubleClick={() => setChatWidth(DEFAULT_CHAT_WIDTH)}
          onKeyDown={handleResizeKeyDown}
          className="group relative cursor-col-resize bg-slate-900 border-x border-slate-800
                     focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500
                     touch-none"
        >
          <div className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2
                          bg-slate-700/70 group-hover:bg-violet-500
                          group-focus-visible:bg-violet-500 transition-colors" />
        </div>

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
