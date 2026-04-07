import logging

from app.ai import clean_text_optional, embed_text
from app.db import get_db


logger = logging.getLogger(__name__)


def create_message_and_embedding(user_id: int, chat_id: int, text: str) -> dict:
    cleaned_text = clean_text_optional(text)

    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO messages (telegram_user_id, chat_id, message_text, cleaned_text)
            VALUES (%s, %s, %s, %s)
            RETURNING id, telegram_user_id, chat_id, message_text, created_at;
            """,
            (user_id, chat_id, text, cleaned_text),
        )
        message = cur.fetchone()
        conn.commit()

    try:
        embedding = embed_text(cleaned_text)

        with get_db() as (conn, cur):
            cur.execute(
                """
                INSERT INTO embeddings (message_id, embedding)
                VALUES (%s, %s::vector);
                """,
                (message["id"], embedding),
            )
            conn.commit()
    except Exception as exc:
        # Capture should still succeed even if embeddings fail.
        logger.exception("Embedding save failed for message %s: %s", message["id"], exc)

    return {
        "id": str(message["id"]),
        "user_id": message["telegram_user_id"],
        "chat_id": message["chat_id"],
        "text": message["message_text"],
        "created_at": message["created_at"],
    }


def search_messages(user_id: int, query: str, limit: int = 5) -> list[dict]:
    query_embedding = embed_text(query)

    with get_db() as (_, cur):
        cur.execute(
            """
            SELECT
              m.id AS message_id,
              m.message_text AS text,
              m.created_at,
              1 - (e.embedding <=> %s::vector) AS similarity
            FROM embeddings e
            JOIN messages m ON m.id = e.message_id
            WHERE m.telegram_user_id = %s
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s;
            """,
            (query_embedding, user_id, query_embedding, limit),
        )
        rows = cur.fetchall()

    return [
        {
            "message_id": str(row["message_id"]),
            "text": row["text"],
            "created_at": row["created_at"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]
