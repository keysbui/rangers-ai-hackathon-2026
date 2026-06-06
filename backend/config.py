import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
MODEL_ID = os.getenv("MODEL_ID", "Seed-2.0-mini-260428")

# Scene detection settings
# SCENE_FALLBACK_ENABLED=true  → fall back to fixed-size chunks when PySceneDetect
#                                 fails or returns 0 scenes (original behaviour).
# SCENE_FALLBACK_ENABLED=false → raise an error instead, forcing PySceneDetect.
SCENE_FALLBACK_ENABLED: bool = os.getenv("SCENE_FALLBACK_ENABLED", "true").lower() == "true"
SCENE_FALLBACK_CHUNK_SEC: int = int(os.getenv("SCENE_FALLBACK_CHUNK_SEC", "30"))

BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage"
RAW_VIDEO_DIR = STORAGE_DIR / "raw_videos"
THUMBNAIL_DIR = STORAGE_DIR / "thumbnails"
DATABASE_PATH = STORAGE_DIR / "db.sqlite3"

for _dir in (RAW_VIDEO_DIR, THUMBNAIL_DIR, STORAGE_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
