import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Clock, Image as ImageIcon, Globe } from "lucide-react";
import { api } from "../api/client";
import { formatSeconds } from "../utils/costTracker";

const LANGUAGES = [
  { code: "vi", label: "Vietnamese" },
  { code: "en", label: "English" },
  { code: "th", label: "ภาษาไทย" },
];

function TimestampChip({ timestamp, onSeek }) {
  if (timestamp == null) return null;
  return (
    <button className="timestamp-chip" onClick={() => onSeek(timestamp)}>
      <Clock size={10} />
      {formatSeconds(timestamp)}
    </button>
  );
}

function Message({ msg, onSeek }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[80%] bg-violet-800/50 border border-violet-700/40 rounded-2xl rounded-tr-sm px-4 py-2.5">
          <div className="flex items-center gap-2 mb-1 text-violet-300">
            <User size={12} />
            <span className="text-[10px] uppercase tracking-wide">You</span>
          </div>
          <p className="text-sm text-slate-100">{msg.content}</p>
        </div>
      </div>
    );
  }

  if (msg.role === "assistant") {
    return (
      <div className="flex mb-3">
        <div className="max-w-[90%] bg-slate-800/60 border border-slate-700/40 rounded-2xl rounded-tl-sm px-4 py-2.5">
          <div className="flex items-center gap-2 mb-1 text-violet-400">
            <Bot size={12} />
            <span className="text-[10px] uppercase tracking-wide">AI</span>
          </div>
          <p className="text-sm text-slate-100 mb-2">{msg.content}</p>

          {msg.timestamp != null && (
            <div className="flex flex-wrap gap-2 mt-2">
              <TimestampChip timestamp={msg.timestamp} onSeek={onSeek} />
              {msg.thumbnail_url && (
                <a
                  href={msg.thumbnail_url}
                  target="_blank"
                  rel="noreferrer"
                  className="timestamp-chip"
                >
                  <ImageIcon size={10} /> Frame
                </a>
              )}
            </div>
          )}

          {msg.reasoning_proof && (
            <p className="text-[11px] text-slate-500 mt-2 italic border-t border-slate-700/40 pt-2">
              {msg.reasoning_proof}
            </p>
          )}
        </div>
      </div>
    );
  }

  if (msg.role === "system") {
    return (
      <div className="text-center text-[11px] text-slate-500 my-2">{msg.content}</div>
    );
  }

  return null;
}

export default function ChatPanel({ videoId, onSeek, onTokensUsed }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("vi");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const SYSTEM_MSG = {
    role: "system",
    content: "Ask anything about the video — timestamps, prices, products, compliance.",
  };

  useEffect(() => {
    if (!videoId) {
      setMessages([SYSTEM_MSG]);
      return;
    }
    api.getQueryHistory(videoId)
      .then((history) => {
        const msgs = [SYSTEM_MSG];
        for (const item of history) {
          msgs.push({ role: "user", content: item.question });
          msgs.push({
            role: "assistant",
            content: item.answer,
            timestamp: item.timestamp,
            timestamp_end: item.timestamp_end,
            thumbnail_url: item.thumbnail_url
              ? `http://localhost:8000${item.thumbnail_url}`
              : null,
            reasoning_proof: item.reasoning_proof,
          });
        }
        setMessages(msgs);
      })
      .catch(() => setMessages([SYSTEM_MSG]));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]);

  const send = async () => {
    const q = input.trim();
    if (!q || !videoId || loading) return;

    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    setLoading(true);

    try {
      const result = await api.query(videoId, q, language);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: result.answer,
          timestamp: result.timestamp,
          timestamp_end: result.timestamp_end,
          thumbnail_url: result.thumbnail_url
            ? `http://localhost:8000${result.thumbnail_url}`
            : null,
          reasoning_proof: result.reasoning_proof,
        },
      ]);
      onTokensUsed?.({
        tokens: result.tokens_used,
        latency_ms: result.latency_ms,
        question: q,
      });
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "system", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full min-h-0 flex flex-col bg-slate-900 border-l border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Bot size={14} className="text-violet-400" /> Q&A
        </h2>
        <div className="flex items-center gap-1">
          <Globe size={12} className="text-slate-400" />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-slate-800 text-slate-300 text-xs rounded px-1.5 py-0.5 border
                       border-slate-700 focus:outline-none focus:border-violet-500"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>{l.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
        {messages.map((m, i) => (
          <Message key={i} msg={m} onSeek={onSeek} />
        ))}
        {loading && (
          <div className="flex mb-3">
            <div className="bg-slate-800/60 border border-slate-700/40 rounded-2xl rounded-tl-sm px-4 py-2.5">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-slate-700/50">
        {!videoId && (
          <p className="text-xs text-slate-500 mb-2 text-center">
            Select a processed video first
          </p>
        )}
        <div className="flex gap-2">
          <input
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2
                       text-sm text-slate-100 placeholder-slate-500
                       focus:outline-none focus:border-violet-500 transition-colors"
            placeholder={language === "vi" ? "Ask about the video..." : language === "th" ? "ถามเกี่ยวกับวิดีโอ..." : "Ask about the video..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            disabled={!videoId || loading}
          />
          <button
            onClick={send}
            disabled={!videoId || loading || !input.trim()}
            className="p-2 rounded-xl bg-violet-700 hover:bg-violet-600 disabled:opacity-40
                       disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} className="text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}
