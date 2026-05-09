# db/chat.py
import uuid
import asyncpg

async def create_session(pool: asyncpg.Pool, history_name: str) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO chat_sessions (history_name)
            VALUES ($1)
            RETURNING session_id
            """,
            history_name,
        )
    result = str(row["session_id"])
    print(f"create_session returning: {result}")  # ← add this
    return result


async def store_chat_history(
    pool: asyncpg.Pool,
    session_id: str,
    question: str,
    answer: str,
) -> str:
    print(f"store_chat_history received session_id: '{session_id}'")  # ← add this
    try:
        parsed = uuid.UUID(session_id)
    except ValueError as e:
        print(f"❌ Invalid UUID: {session_id}")
        raise

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO chat_messages (session_id, question, answer)
            VALUES ($1, $2, $3)
            RETURNING message_id
            """,
            parsed,
            question,
            answer,
        )
    return str(row["message_id"])


async def get_chat_history(
    pool: asyncpg.Pool,
    session_id: str,
    limit: int = 50,
) -> list[dict]:
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT message_id, question, answer, timestamp
                FROM   chat_messages
                WHERE  session_id = $1
                ORDER  BY timestamp ASC
                LIMIT  $2
                """,
                uuid.UUID(session_id),
                limit,
            )
        return [dict(r) for r in rows]
    except Exception:
        return []