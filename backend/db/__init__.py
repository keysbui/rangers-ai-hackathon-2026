import sqlite3
from pathlib import Path
from contextlib import contextmanager
from config import DATABASE_PATH

_SCHEMA = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    sql = _SCHEMA.read_text()
    with get_db() as conn:
        conn.executescript(sql)
        
        # Migration: Ensure new columns exist in Highlights
        try:
            cursor = conn.execute("PRAGMA table_info(Highlights)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns:
                if "viral_score" not in columns:
                    conn.execute("ALTER TABLE Highlights ADD COLUMN viral_score REAL DEFAULT 0.0")
                if "refined_start" not in columns:
                    conn.execute("ALTER TABLE Highlights ADD COLUMN refined_start REAL")
                if "refined_end" not in columns:
                    conn.execute("ALTER TABLE Highlights ADD COLUMN refined_end REAL")
        except Exception:
            pass
