"""PostgreSQL database utilities using asyncpg."""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator
from uuid import UUID

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manages the asyncpg connection pool."""

    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            return

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self._pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
        )
        logger.info("Database pool initialized")

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire a connection from the pool."""
        if self._pool is None:
            await self.initialize()
        async with self._pool.acquire() as conn:
            yield conn


# Global pool instance
db_pool = DatabasePool()


async def initialize_database() -> None:
    """Initialize the database connection pool."""
    await db_pool.initialize()


async def close_database() -> None:
    """Close the database connection pool."""
    await db_pool.close()


# =============================================================================
# Session Operations
# =============================================================================


async def create_session(
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    timeout_minutes: int = 60,
) -> str:
    """Create a new session.

    Args:
        user_id: Optional user identifier.
        metadata: Optional session metadata.
        timeout_minutes: Session timeout in minutes.

    Returns:
        Session ID as string.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, metadata, expires_at)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            user_id,
            json.dumps(metadata or {}),
            expires_at,
        )
        return str(row["id"])


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Get a session by ID.

    Args:
        session_id: Session UUID string.

    Returns:
        Session dict if found, None otherwise.
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, metadata, created_at, updated_at, expires_at
            FROM sessions WHERE id = $1
            """,
            UUID(session_id),
        )
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "user_id": row["user_id"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
        }


# =============================================================================
# Message Operations
# =============================================================================


async def add_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Add a message to a session.

    Args:
        session_id: Session UUID string.
        role: Message role (user, assistant, system, tool).
        content: Message content.
        metadata: Optional metadata.

    Returns:
        Message ID as string.
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (session_id, role, content, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            UUID(session_id),
            role,
            content,
            json.dumps(metadata or {}),
        )
        return str(row["id"])


async def get_session_messages(
    session_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get messages for a session.

    Args:
        session_id: Session UUID string.
        limit: Maximum messages to return.

    Returns:
        List of message dicts ordered by creation time.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, role, content, metadata, created_at
            FROM messages
            WHERE session_id = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            UUID(session_id),
            limit,
        )
        return [
            {
                "id": str(row["id"]),
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]


# =============================================================================
# Vector Search Operations
# =============================================================================


async def vector_search(
    embedding: list[float],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search for similar chunks using vector similarity.

    Args:
        embedding: Query embedding vector.
        limit: Maximum results to return.

    Returns:
        List of matching chunk dicts.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM match_chunks($1::vector, $2)",
            str(embedding),
            limit,
        )
        return [
            {
                "chunk_id": str(row["chunk_id"]),
                "document_id": str(row["document_id"]),
                "document_title": row["document_title"],
                "document_source": row["document_source"],
                "content": row["content"],
                "chunk_index": row["chunk_index"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "score": float(row["similarity"]),
            }
            for row in rows
        ]


async def hybrid_search(
    embedding: list[float],
    query_text: str,
    limit: int = 10,
    text_weight: float = 0.3,
) -> list[dict[str, Any]]:
    """Perform hybrid vector + text search.

    Args:
        embedding: Query embedding vector.
        query_text: Query text for full-text search.
        limit: Maximum results to return.
        text_weight: Weight for text similarity (0-1).

    Returns:
        List of matching chunk dicts with combined scores.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM hybrid_search($1::vector, $2, $3, $4)",
            str(embedding),
            query_text,
            limit,
            text_weight,
        )
        return [
            {
                "chunk_id": str(row["chunk_id"]),
                "document_id": str(row["document_id"]),
                "document_title": row["document_title"],
                "document_source": row["document_source"],
                "content": row["content"],
                "chunk_index": row["chunk_index"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "score": float(row["combined_score"]),
            }
            for row in rows
        ]


# =============================================================================
# Document Operations
# =============================================================================


async def list_documents(
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List all documents with chunk counts.

    Args:
        limit: Maximum documents to return.
        offset: Number of documents to skip.

    Returns:
        List of document dicts with chunk_count.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.id, d.title, d.source, d.metadata, d.created_at, d.updated_at,
                   COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.document_id
            GROUP BY d.id, d.title, d.source, d.metadata, d.created_at, d.updated_at
            ORDER BY d.title
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "source": row["source"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
                "chunk_count": row["chunk_count"],
            }
            for row in rows
        ]


async def get_document(document_id: str) -> dict[str, Any] | None:
    """Get a document by ID.

    Args:
        document_id: Document UUID string.

    Returns:
        Document dict if found, None otherwise.
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, title, source, content, metadata, created_at, updated_at
            FROM documents WHERE id = $1
            """,
            UUID(document_id),
        )
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "source": row["source"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }


# =============================================================================
# Ingestion Operations
# =============================================================================


async def get_document_by_title(title: str) -> dict[str, Any] | None:
    """Get a document by its title.

    Args:
        title: Document title to look up.

    Returns:
        Document dict if found, None otherwise.
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, title, source, content, metadata, created_at, updated_at
            FROM documents WHERE title = $1
            """,
            title,
        )
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "source": row["source"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }


async def delete_document(document_id: str) -> bool:
    """Delete a document by ID. Cascades to chunks via FK.

    Args:
        document_id: Document UUID string.

    Returns:
        True if a document was deleted.
    """
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM documents WHERE id = $1",
            UUID(document_id),
        )
        return result == "DELETE 1"


async def create_document(
    title: str,
    source: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new document.

    Args:
        title: Document title.
        source: Document source path.
        content: Full document content.
        metadata: Optional metadata dict.

    Returns:
        Dict with document fields including 'id'.
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO documents (title, source, content, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING id, title, source, created_at, updated_at
            """,
            title,
            source,
            content,
            json.dumps(metadata or {}),
        )
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "source": row["source"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }


async def create_chunk(
    document_id: str,
    content: str,
    chunk_index: int,
    embedding: list[float],
    metadata: dict[str, Any] | None = None,
    token_count: int | None = None,
) -> str:
    """Create a new chunk with its embedding.

    Args:
        document_id: Parent document UUID string.
        content: Chunk text content.
        chunk_index: Position index within the document.
        embedding: Embedding vector (1536 dimensions).
        metadata: Optional metadata dict.
        token_count: Optional token count.

    Returns:
        Chunk ID as string.
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO chunks (document_id, content, chunk_index, embedding, metadata, token_count)
            VALUES ($1, $2, $3, $4::vector, $5, $6)
            RETURNING id
            """,
            UUID(document_id),
            content,
            chunk_index,
            str(embedding),
            json.dumps(metadata or {}),
            token_count or 0,
        )
        return str(row["id"])


async def close_db_pool() -> None:
    """Close the database connection pool. Alias for close_database()."""
    await close_database()


# =============================================================================
# Health Check
# =============================================================================


async def test_connection() -> bool:
    """Test if database is accessible.

    Returns:
        True if database is healthy.
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
