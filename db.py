import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "kits.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    schema = (BASE_DIR / "schema.sql").read_text()
    conn = get_db()
    conn.executescript(schema)
    conn.commit()
    conn.close()


def like_pattern(text):
    """Turn search text into a LIKE pattern that matches it anywhere.

    %, _ and \\ are escaped so they match literally. Use with ESCAPE '\\'.
    """
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"