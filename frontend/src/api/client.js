const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(method, path, body, isFormData = false) {
  const opts = { method, headers: {} };
  if (body) {
    if (isFormData) {
      opts.body = body;
    } else {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
  }
  const res = await fetch(`${BASE_URL}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  // Videos
  uploadVideo: (formData) => request("POST", "/api/videos", formData, true),
  listVideos: () => request("GET", "/api/videos"),
  getVideo: (id) => request("GET", `/api/videos/${id}`),
  deleteVideo: (id) => request("DELETE", `/api/videos/${id}`),
  getTimeline: (id) => request("GET", `/api/videos/${id}/timeline`),
  getHighlights: (id, trends, refresh = false) => {
    const params = new URLSearchParams();
    if (trends) params.append("trends", trends);
    if (refresh) params.append("refresh", "true");
    const q = params.toString() ? `?${params.toString()}` : "";
    return request("GET", `/api/videos/${id}/highlights${q}`);
  },
  reprocessVideo: (id) => request("POST", `/api/videos/${id}/process`),
  streamUrl: (id) => `${BASE_URL}/api/videos/${id}/stream`,

  // Query
  query: (videoId, question, language = "vi") =>
    request("POST", "/api/query", { video_id: videoId, question, language }),

  // Compliance
  getCompliance: (videoId) => request("GET", `/api/compliance/${videoId}`),

  // Thumbnails
  thumbnailUrl: (videoId, ts) => {
    const idx = Math.max(1, Math.round(ts) + 1);
    return `${BASE_URL}/thumbnails/${videoId}/${String(idx).padStart(6, "0")}.jpg`;
  },
};
