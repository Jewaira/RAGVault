# db/init.py
import asyncpg
from db.config import DBConfig

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    history_name TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID        NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    question    TEXT        NOT NULL,
    answer      TEXT        NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
    ON chat_messages(session_id);
"""

async def create_database_if_not_exists(config: DBConfig):
    """Connect to default 'postgres' database and create 'chatdb' if it doesn't exist."""
    conn = await asyncpg.connect(
        host=config.host,
        port=config.port,
        database="postgres",   # ← connect to default db first
        user=config.user,
        password=config.password,
    )
    try:
        # check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            config.database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{config.database}"')
            print(f" Database '{config.database}' created.")
        else:
            print(f" Database '{config.database}' already exists.")
    finally:
        await conn.close()


async def get_pool(config: DBConfig) -> asyncpg.Pool:
    """Create and return a connection pool."""
    return await asyncpg.create_pool(
        host=config.host,
        port=config.port,
        database=config.database,
        user=config.user,
        password=config.password,
        min_size=2,
        max_size=10,
    )


async def init_db(pool: asyncpg.Pool):
    """Create tables if they don't exist. Safe to call on every startup."""
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLES_SQL)
    print("Database tables initialized.")