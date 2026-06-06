PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS Videos (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT,
    duration    REAL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Timeline_Metadata (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL REFERENCES Videos(id) ON DELETE CASCADE,
    timestamp_start REAL NOT NULL,
    timestamp_end   REAL NOT NULL,
    transcript      TEXT,
    ocr_text        TEXT,
    audio_event     TEXT,
    detected_skus   TEXT,
    energy_score    REAL DEFAULT 0.0,
    thumbnail_url   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tm_video_id ON Timeline_Metadata(video_id);
CREATE INDEX IF NOT EXISTS idx_tm_ts ON Timeline_Metadata(timestamp_start);

-- FTS5 virtual table for fast full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS Timeline_FTS USING fts5(
    transcript,
    ocr_text,
    detected_skus,
    content=Timeline_Metadata,
    content_rowid=id
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS tm_ai AFTER INSERT ON Timeline_Metadata BEGIN
    INSERT INTO Timeline_FTS(rowid, transcript, ocr_text, detected_skus)
    VALUES (new.id, new.transcript, new.ocr_text, new.detected_skus);
END;

CREATE TRIGGER IF NOT EXISTS tm_ad AFTER DELETE ON Timeline_Metadata BEGIN
    INSERT INTO Timeline_FTS(Timeline_FTS, rowid, transcript, ocr_text, detected_skus)
    VALUES ('delete', old.id, old.transcript, old.ocr_text, old.detected_skus);
END;

CREATE TRIGGER IF NOT EXISTS tm_au AFTER UPDATE ON Timeline_Metadata BEGIN
    INSERT INTO Timeline_FTS(Timeline_FTS, rowid, transcript, ocr_text, detected_skus)
    VALUES ('delete', old.id, old.transcript, old.ocr_text, old.detected_skus);
    INSERT INTO Timeline_FTS(rowid, transcript, ocr_text, detected_skus)
    VALUES (new.id, new.transcript, new.ocr_text, new.detected_skus);
END;

CREATE TABLE IF NOT EXISTS Highlights (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL REFERENCES Videos(id) ON DELETE CASCADE,
    timestamp_start REAL NOT NULL,
    timestamp_end   REAL NOT NULL,
    reason          TEXT,
    ad_copy         TEXT,
    thumbnail_url   TEXT,
    energy_score    REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_highlights_video_id ON Highlights(video_id);
