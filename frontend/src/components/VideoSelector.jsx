import { useState, useEffect } from "react";
import { Upload, Link, RefreshCw, CheckCircle, Loader, AlertCircle, Trash2 } from "lucide-react";
import { api } from "../api/client";

const STATUS_ICON = {
  pending: <Loader size={12} className="text-slate-400" />,
  processing: <Loader size={12} className="text-yellow-400 animate-spin" />,
  done: <CheckCircle size={12} className="text-green-400" />,
  error: <AlertCircle size={12} className="text-red-400" />,
};

export default function VideoSelector({ selectedId, onSelect }) {
  const [videos, setVideos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [tab, setTab] = useState("file"); // "file" | "url"

  const refresh = async () => {
    try {
      const data = await api.listVideos();
      setVideos(data);
    } catch (err) {
      console.error("Failed to refresh video list", err);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const initialRefresh = async () => {
      if (isMounted) await refresh();
    };
    initialRefresh();
    
    const timer = setInterval(refresh, 4000);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, []);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("auto_process", "true");
    try {
      const v = await api.uploadVideo(fd);
      await refresh();
      onSelect(v);
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleUrl = async () => {
    if (!urlInput.trim()) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("url", urlInput.trim());
    fd.append("auto_process", "true");
    try {
      const v = await api.uploadVideo(fd);
      await refresh();
      onSelect(v);
      setUrlInput("");
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this video and all its analysis data?")) return;
    try {
      await api.deleteVideo(id);
      await refresh();
      if (selectedId === id) {
        onSelect(null);
      }
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="bg-slate-900 border-b border-slate-700/50 px-4 py-2">
      <div className="flex items-center gap-4 flex-wrap">
        {/* Upload tabs */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setTab("file")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors
              ${tab === "file" ? "bg-violet-700 text-white" : "bg-slate-800 text-slate-400 hover:text-slate-200"}`}
          >
            <Upload size={12} /> File
          </button>
          <button
            onClick={() => setTab("url")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors
              ${tab === "url" ? "bg-violet-700 text-white" : "bg-slate-800 text-slate-400 hover:text-slate-200"}`}
          >
            <Link size={12} /> URL
          </button>
        </div>

        {tab === "file" && (
          <label className={`cursor-pointer flex items-center gap-2 px-3 py-1.5 rounded-lg
                             border border-dashed border-slate-600 text-xs text-slate-400
                             hover:border-violet-500 hover:text-slate-200 transition-colors
                             ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
            {uploading ? <Loader size={12} className="animate-spin" /> : <Upload size={12} />}
            {uploading ? "Uploading..." : "Choose video"}
            <input type="file" accept="video/*" className="hidden" onChange={handleFile} />
          </label>
        )}

        {tab === "url" && (
          <div className="flex gap-2">
            <input
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5
                         text-xs text-slate-200 placeholder-slate-500 w-64
                         focus:outline-none focus:border-violet-500"
              placeholder="https://..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleUrl()}
            />
            <button
              onClick={handleUrl}
              disabled={uploading || !urlInput.trim()}
              className="px-3 py-1.5 bg-violet-700 hover:bg-violet-600 disabled:opacity-40
                         rounded-lg text-xs text-white transition-colors"
            >
              {uploading ? "..." : "Add"}
            </button>
          </div>
        )}

        {/* Video list */}
        <div className="flex items-center gap-2 overflow-x-auto flex-1">
          {videos.map((v) => (
            <div
              key={v.id}
              className={`flex items-center gap-0 rounded-lg text-xs whitespace-nowrap
                          transition-colors border group
                          ${selectedId === v.id
                            ? "bg-violet-800/60 border-violet-600 text-violet-200"
                            : "bg-slate-800/60 border-slate-700/40 text-slate-400 hover:border-slate-600"}`}
            >
              <button
                onClick={() => onSelect(v)}
                className="flex items-center gap-1.5 px-3 py-1.5 hover:text-slate-200"
              >
                {STATUS_ICON[v.status]}
                <span className="max-w-[120px] truncate">{v.name}</span>
              </button>
              <button
                onClick={(e) => handleDelete(e, v.id)}
                className="pr-2 py-1.5 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete video"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>

        <button
          onClick={refresh}
          className="ml-auto p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400
                     hover:text-slate-200 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={12} />
        </button>
      </div>
    </div>
  );
}
