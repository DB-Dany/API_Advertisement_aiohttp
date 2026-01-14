import asyncpg
from typing import Any
from config import Config

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ADS_SQL = """
CREATE TABLE IF NOT EXISTS advertisements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_advertisements_user_id ON advertisements(user_id);
"""


async def create_pool(cfg: Config) -> asyncpg.Pool:
    # Асинхронный пул соединений — самый правильный подход для aiohttp
    return await asyncpg.create_pool(
        dsn=cfg.dsn,
        min_size=1,
        max_size=10,
    )


async def init_db(pool: asyncpg.Pool) -> None:
    # Создаём таблицы при старте (упрощённый вариант “миграций”)
    async with pool.acquire() as conn:
        await conn.execute(CREATE_USERS_SQL)
        await conn.execute(CREATE_ADS_SQL)
        await conn.execute(CREATE_INDEX_SQL)


def row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    d = dict(row)
    # created_at -> isoformat для JSON
    if "created_at" in d and d["created_at"] is not None:
        d["created_at"] = d["created_at"].isoformat()
    return d