import aiosqlite
from datetime import datetime

DB_PATH = "bot.db"

BOOKINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    service TEXT,
    duration_min INTEGER,
    price INTEGER,
    comment TEXT,
    date TEXT,
    time TEXT,
    status TEXT DEFAULT 'submitted',
    created_at TEXT
);
"""

# Попытка добавить недостающие колонки при апгрейде старых баз (тихая миграция)
MIGRATIONS = [
    "ALTER TABLE bookings ADD COLUMN service TEXT",
    "ALTER TABLE bookings ADD COLUMN duration_min INTEGER",
    "ALTER TABLE bookings ADD COLUMN price INTEGER",
    "ALTER TABLE bookings ADD COLUMN comment TEXT",
    "ALTER TABLE bookings ADD COLUMN date TEXT",
    "ALTER TABLE bookings ADD COLUMN time TEXT",
    "ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'submitted'",
    "ALTER TABLE bookings ADD COLUMN created_at TEXT"
]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(BOOKINGS_TABLE_SQL)
        await db.commit()

        # Пытаемся безопасно добавить колонки, если их нет (игнорируем ошибки)
        cur = await db.execute("PRAGMA table_info(bookings)")
        rows = await cur.fetchall()
        existing = {r[1] for r in rows}
        cols_to_try = {
            "service": "ALTER TABLE bookings ADD COLUMN service TEXT",
            "duration_min": "ALTER TABLE bookings ADD COLUMN duration_min INTEGER",
            "price": "ALTER TABLE bookings ADD COLUMN price INTEGER",
            "comment": "ALTER TABLE bookings ADD COLUMN comment TEXT",
            "date": "ALTER TABLE bookings ADD COLUMN date TEXT",
            "time": "ALTER TABLE bookings ADD COLUMN time TEXT",
            "status": "ALTER TABLE bookings ADD COLUMN status TEXT",
            "created_at": "ALTER TABLE bookings ADD COLUMN created_at TEXT"
        }
        for col, sql in cols_to_try.items():
            if col not in existing:
                try:
                    await db.execute(sql)
                except Exception:
                    # возможны ошибки при повторной миграции — игнорируем
                    pass
        await db.commit()


async def add_booking(
    user_id: int,
    username: str,
    service: str,
    duration_min: int,
    price: int,
    comment: str,
    date: str,
    time: str,
    status: str = "submitted",
):
    created_at = datetime.utcnow().isoformat() + "Z"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO bookings (user_id, username, service, duration_min, price, comment, date, time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, service, duration_min, price, comment, date, time, status, created_at)
        )
        await db.commit()


async def get_bookings_by_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, service, duration_min, price, date, time, status, created_at
            FROM bookings
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,))
        return await cur.fetchall()
