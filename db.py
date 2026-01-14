import asyncpg
from typing import Any
from config import Config


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS advertisements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    owner VARCHAR(100) NOT NULL
);
"""


async def create_pool(cfg: Config) -> asyncpg.Pool:
    # Создаём пул соединений
    return await asyncpg.create_pool(
        dsn=cfg.dsn,
        min_size=1,
        max_size=10,
    )


async def init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)


def row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    d = dict(row)
    # created_at -> isoformat
    if "created_at" in d and d["created_at"] is not None:
        d["created_at"] = d["created_at"].isoformat()
    return d
