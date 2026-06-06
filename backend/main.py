from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import init_db
from api.videos import router as videos_router
from api.query import router as query_router
from api.compliance import router as compliance_router
from api.policy_audit import router as policy_audit_router
from config import THUMBNAIL_DIR, STORAGE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    init_db()
    yield


app = FastAPI(
    title="Video Intelligence Engine",
    description="Multimodal RAG system for Southeast Asian e-commerce videos",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos_router)
app.include_router(query_router)
app.include_router(compliance_router)
app.include_router(policy_audit_router)

app.mount("/thumbnails", StaticFiles(directory=str(THUMBNAIL_DIR)), name="thumbnails")


@app.get("/health")
def health():
    return {"status": "ok", "model": "Seed-2.0-mini-260428"}
