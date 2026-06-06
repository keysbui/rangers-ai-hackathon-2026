# Video Intelligence Engine (BX-T4)

Multimodal RAG system for Southeast Asian e-commerce videos, powered by **Seed-2.0-mini-260428** via BytePlus ModelArk.

## Features

- **Video Upload**: local file or URL
- **Auto Scene Detection**: PySceneDetect splits video into shots
- **Frame Extraction**: ffmpeg @ 1fps -> JPEG thumbnails
- **Multimodal Analysis**: Seed-2.0-mini extracts transcript (ASR), OCR text (prices/vouchers), audio events, detected SKUs, energy score per segment
- **Two-Stage Retrieval**: FTS5 keyword filter + Seed deep reasoning -> grounded answers with timestamp + thumbnail
- **Compliance Audit**: auto-detect spoken claims vs. on-screen text mismatches
- **3-Column UI**: Timeline explorer | Video player + Energy Curve | Multilingual Q&A chatbot
- **Cost & Latency Dashboard**: realtime token usage, USD cost, per-query latency chart

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- `ffmpeg` installed (`brew install ffmpeg`)
- BytePlus ModelArk API key

### 1. Clone & configure

```bash
git clone <repo-url>
cd video-intelligence-engine
cp .env.example .env
# Edit .env: set ARK_API_KEY=your_key_here
```

### 2. Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at http://localhost:8000
API docs: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/videos` | POST | Upload video (file or URL) |
| `/api/videos` | GET | List all videos |
| `/api/videos/{id}` | GET | Get video status |
| `/api/videos/{id}/timeline` | GET | Get all segments with metadata |
| `/api/videos/{id}/process` | POST | Re-trigger processing |
| `/api/query` | POST | Ask a question about a processed video |
| `/api/compliance/{id}` | GET | Run compliance audit |

### Query request example

```json
POST /api/query
{
  "video_id": "uuid-here",
  "question": "What is the price of the iPhone?",
  "language": "en"
}
```

### Query response example

```json
{
  "answer": "iPhone 15 Pro is sold for 28,990,000 VND",
  "timestamp": 143.0,
  "timestamp_end": 158.0,
  "thumbnail_url": "/thumbnails/uuid/000144.jpg",
  "reasoning_proof": "At 2:23, the host shows the price tag '28.99 million' on screen while saying 'genuine price'",
  "tokens_used": {"input": 1240, "output": 87, "cache_read": 890},
  "latency_ms": 1823.4
}
```

## Project Structure

```
video-intelligence-engine/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Env vars + path config
│   ├── requirements.txt
│   ├── api/
│   │   ├── videos.py        # Upload, list, process endpoints
│   │   ├── query.py         # Q&A endpoint
│   │   └── compliance.py    # Compliance audit endpoint
│   ├── services/
│   │   ├── pipeline.py      # Orchestrates full processing
│   │   ├── scene_service.py # PySceneDetect shot detection
│   │   ├── frame_service.py # ffmpeg frame extraction
│   │   ├── seed_client.py   # ModelArk Seed-2.0-mini API client
│   │   └── retrieval.py     # Two-stage retrieval engine
│   ├── models/              # Pydantic request/response models
│   └── db/
│       ├── schema.sql        # SQLite schema + FTS5 triggers
│       └── __init__.py       # DB connection helpers
├── frontend/
│   └── src/
│       ├── App.jsx           # 3-column layout root
│       ├── components/
│       │   ├── TimelineExplorer.jsx
│       │   ├── VideoPlayer.jsx
│       │   ├── ChatPanel.jsx
│       │   ├── VideoSelector.jsx
│       │   └── CostDashboard.jsx
│       ├── api/client.js     # API calls
│       └── utils/costTracker.js
└── storage/
    ├── raw_videos/           # Uploaded video files
    ├── thumbnails/{video_id}/# Extracted frames
    └── db.sqlite3            # SQLite database
```

## Cost Estimation

| Token type | Price |
|---|---|
| Input | $0.15 / 1M tokens |
| Cache Read | $0.04 / 1M tokens |
| Output | $0.60 / 1M tokens |

A 15-minute video with ~30 scenes costs approximately **$0.05–0.15** to process.
Each Q&A query costs approximately **$0.001–0.003** (less with cache hits).

## Languages Supported

- Vietnamese — primary
- English
- ภาษาไทย (Thai)

## Hard Constraints Met

- [x] Uses `Seed-2.0-mini-260428` for all multimodal tasks
- [x] Every Q&A answer includes timestamp + thumbnail (Grounded Answer)
- [x] Compliance workflow (`GET /api/compliance/{id}`)
- [x] Supports Vietnamese + English + Thai
- [x] UI shows Cost + Latency dashboard in real time
