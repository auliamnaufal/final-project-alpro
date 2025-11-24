import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "helmet_monitor.db"
MIGRATION = ROOT / "migrations" / "001_init.sql"


def run():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    sql = MIGRATION.read_text()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    run()
