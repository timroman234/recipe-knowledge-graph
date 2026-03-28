"""Embedding generation for recipe text chunks."""

import asyncio
import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EmbedderConfig:
    """Configuration for embedding generation."""

    model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    batch_size: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0


class Embedder:
    """Embedding generator using OpenAI API."""

    def __init__(self, config: EmbedderConfig | None = None):
        """Initialize the embedder.

        Args:
            config: Optional configuration.
        """
        self.config = config or EmbedderConfig()
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")
            base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
            self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.embeddings.create(
                    input=text,
                    model=self.config.model,
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    logger.error(f"Failed to embed text after {self.config.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Embedding attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        raise RuntimeError("Failed to generate embedding")

    async def embed_batch(
        self,
        texts: list[str],
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts with batching.

        Args:
            texts: List of texts to embed.
            show_progress: Whether to log progress.

        Returns:
            List of embedding vectors.
        """
        embeddings: list[list[float]] = []
        total_batches = (len(texts) + self.config.batch_size - 1) // self.config.batch_size

        for batch_idx in range(0, len(texts), self.config.batch_size):
            batch = texts[batch_idx : batch_idx + self.config.batch_size]
            current_batch = batch_idx // self.config.batch_size + 1

            if show_progress:
                logger.info(f"Embedding batch {current_batch}/{total_batches}")

            for attempt in range(self.config.max_retries):
                try:
                    response = await self.client.embeddings.create(
                        input=batch,
                        model=self.config.model,
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    if attempt == self.config.max_retries - 1:
                        logger.error(
                            f"Failed to embed batch {current_batch} after "
                            f"{self.config.max_retries} attempts: {e}"
                        )
                        raise
                    logger.warning(
                        f"Batch {current_batch} attempt {attempt + 1} failed, retrying: {e}"
                    )
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

            # Rate limiting delay between batches
            if batch_idx + self.config.batch_size < len(texts):
                await asyncio.sleep(0.1)

        return embeddings


# Module-level convenience functions


async def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text.

    Args:
        text: Text to embed.

    Returns:
        Embedding vector.
    """
    embedder = Embedder()
    return await embedder.embed_text(text)


async def embed_batch(
    texts: list[str],
    show_progress: bool = False,
) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed.
        show_progress: Whether to log progress.

    Returns:
        List of embedding vectors.
    """
    embedder = Embedder()
    return await embedder.embed_batch(texts, show_progress)
