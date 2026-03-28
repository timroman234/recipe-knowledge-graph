"""Tests for the embedding generator."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from ingestion.embedder import Embedder, EmbedderConfig, embed_text, embed_batch


@pytest.mark.unit
class TestEmbedderConfig:
    """Tests for EmbedderConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EmbedderConfig()

        assert config.model == "text-embedding-3-small" or "embedding" in config.model.lower()
        assert config.batch_size == 10
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EmbedderConfig(
            model="custom-model",
            batch_size=5,
            max_retries=5,
            retry_delay=2.0,
        )

        assert config.model == "custom-model"
        assert config.batch_size == 5
        assert config.max_retries == 5
        assert config.retry_delay == 2.0


@pytest.mark.unit
class TestEmbedderEmbedText:
    """Tests for single text embedding."""

    @pytest.mark.asyncio
    async def test_embed_text_returns_vector(self, sample_embedding):
        """Test that embed_text returns an embedding vector."""
        embedder = Embedder()

        with patch.object(embedder, "client", new_callable=MagicMock) as mock_client:
            mock_response = MagicMock()
            mock_data = MagicMock()
            mock_data.embedding = sample_embedding
            mock_response.data = [mock_data]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await embedder.embed_text("test text")

            assert len(result) == 1536
            assert result == sample_embedding

    @pytest.mark.asyncio
    async def test_embed_text_retries_on_error(self, sample_embedding):
        """Test that embed_text retries on transient errors."""
        config = EmbedderConfig(max_retries=3, retry_delay=0.01)
        embedder = Embedder(config)

        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            mock_response = MagicMock()
            mock_data = MagicMock()
            mock_data.embedding = sample_embedding
            mock_response.data = [mock_data]
            return mock_response

        with patch.object(embedder, "client", new_callable=MagicMock) as mock_client:
            mock_client.embeddings.create = mock_create

            result = await embedder.embed_text("test text")

            assert call_count == 3
            assert len(result) == 1536


@pytest.mark.unit
class TestEmbedderEmbedBatch:
    """Tests for batch embedding."""

    @pytest.mark.asyncio
    async def test_embed_batch_returns_multiple_vectors(self, sample_embedding):
        """Test that embed_batch returns multiple embeddings."""
        embedder = Embedder()
        texts = ["text 1", "text 2", "text 3"]

        with patch.object(embedder, "client", new_callable=MagicMock) as mock_client:
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=sample_embedding) for _ in range(3)
            ]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            results = await embedder.embed_batch(texts)

            assert len(results) == 3
            assert all(len(r) == 1536 for r in results)

    @pytest.mark.asyncio
    async def test_embed_batch_respects_batch_size(self, sample_embedding):
        """Test that embed_batch respects batch_size config."""
        config = EmbedderConfig(batch_size=2)
        embedder = Embedder(config)
        texts = ["text 1", "text 2", "text 3", "text 4", "text 5"]

        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            input_texts = kwargs.get("input", args[0] if args else [])
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=sample_embedding) for _ in input_texts
            ]
            return mock_response

        with patch.object(embedder, "client", new_callable=MagicMock) as mock_client:
            mock_client.embeddings.create = mock_create

            results = await embedder.embed_batch(texts)

            # With batch_size=2 and 5 texts, we should have 3 batches
            assert call_count == 3
            assert len(results) == 5


@pytest.mark.unit
class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_embed_text_function(self, sample_embedding):
        """Test the module-level embed_text function."""
        with patch("ingestion.embedder.Embedder") as MockEmbedder:
            mock_instance = MockEmbedder.return_value
            mock_instance.embed_text = AsyncMock(return_value=sample_embedding)

            result = await embed_text("test text")

            assert len(result) == 1536
            mock_instance.embed_text.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_embed_batch_function(self, sample_embedding):
        """Test the module-level embed_batch function."""
        with patch("ingestion.embedder.Embedder") as MockEmbedder:
            mock_instance = MockEmbedder.return_value
            mock_instance.embed_batch = AsyncMock(return_value=[sample_embedding] * 3)

            result = await embed_batch(["text 1", "text 2", "text 3"])

            assert len(result) == 3
            mock_instance.embed_batch.assert_called_once()
