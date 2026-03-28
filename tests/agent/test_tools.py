"""Tests for agent tools."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from agent import tools
from agent.models import ChunkResult, GraphSearchResult


@pytest.mark.unit
class TestVectorSearch:
    """Tests for vector search tool."""

    @pytest.mark.asyncio
    async def test_vector_search_returns_results(self, sample_embedding):
        """Test that vector search returns formatted results."""
        mock_db_results = [
            {
                "chunk_id": str(uuid4()),
                "document_id": str(uuid4()),
                "document_title": "Tacos al Pastor",
                "document_source": "Tacos al Pastor.md",
                "content": "Test content about tacos",
                "chunk_index": 0,
                "metadata": {"cuisine": "Mexican"},
                "score": 0.95,
            }
        ]

        with patch("agent.tools.generate_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = sample_embedding

            with patch("agent.tools.db_utils.vector_search", new_callable=AsyncMock) as mock_vs:
                mock_vs.return_value = mock_db_results

                input_model = tools.VectorSearchInput(query="tacos with cilantro", limit=5)
                results = await tools.vector_search_tool(input_model)

                assert len(results) == 1
                assert isinstance(results[0], ChunkResult)
                assert results[0].document_title == "Tacos al Pastor"
                assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_vector_search_respects_limit(self, sample_embedding):
        """Test that vector search respects the limit parameter."""
        with patch("agent.tools.generate_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = sample_embedding

            with patch("agent.tools.db_utils.vector_search", new_callable=AsyncMock) as mock_vs:
                mock_vs.return_value = []

                input_model = tools.VectorSearchInput(query="test query", limit=3)
                await tools.vector_search_tool(input_model)

                mock_vs.assert_called_once_with(sample_embedding, limit=3)


@pytest.mark.unit
class TestGraphSearch:
    """Tests for graph search tool."""

    @pytest.mark.asyncio
    async def test_graph_search_returns_results(self):
        """Test that graph search returns GraphSearchResult models."""
        mock_results = [
            {
                "fact": "Tacos al Pastor uses cilantro",
                "uuid": str(uuid4()),
                "valid_at": None,
                "invalid_at": None,
                "source_node_uuid": None,
            }
        ]

        with patch(
            "agent.tools.graph_utils.search_knowledge_graph", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_results

            input_model = tools.GraphSearchInput(query="recipes with cilantro", limit=10)
            results = await tools.graph_search_tool(input_model)

            assert len(results) == 1
            assert isinstance(results[0], GraphSearchResult)
            assert "cilantro" in results[0].fact

    @pytest.mark.asyncio
    async def test_graph_search_handles_empty_results(self):
        """Test that graph search handles empty results gracefully."""
        with patch(
            "agent.tools.graph_utils.search_knowledge_graph", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = []

            input_model = tools.GraphSearchInput(query="nonexistent query")
            results = await tools.graph_search_tool(input_model)

            assert results == []


@pytest.mark.unit
class TestHybridSearch:
    """Tests for hybrid search tool."""

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_chunk_results(self, sample_embedding):
        """Test that hybrid search returns ChunkResult models."""
        mock_db_results = [
            {
                "chunk_id": str(uuid4()),
                "document_id": str(uuid4()),
                "document_title": "Tacos al Pastor",
                "document_source": "Tacos al Pastor.md",
                "content": "Hybrid result content",
                "chunk_index": 0,
                "metadata": {},
                "score": 0.85,
            }
        ]

        with patch("agent.tools.generate_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = sample_embedding

            with patch("agent.tools.db_utils.hybrid_search", new_callable=AsyncMock) as mock_hs:
                mock_hs.return_value = mock_db_results

                input_model = tools.HybridSearchInput(query="test query", limit=10)
                results = await tools.hybrid_search_tool(input_model)

                assert len(results) == 1
                assert isinstance(results[0], ChunkResult)
                assert results[0].document_title == "Tacos al Pastor"


@pytest.mark.unit
class TestGetDocument:
    """Tests for get document tool."""

    @pytest.mark.asyncio
    async def test_get_document_returns_document(self):
        """Test that get_document returns document dict."""
        doc_id = str(uuid4())
        mock_doc = {
            "id": doc_id,
            "title": "Test Recipe",
            "source": "Test Recipe.md",
            "content": "Recipe content",
            "metadata": {"cuisine": "Mexican"},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        with patch("agent.tools.db_utils.get_document", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_doc

            input_model = tools.DocumentInput(document_id=doc_id)
            result = await tools.get_document_tool(input_model)

            assert result is not None
            assert result["title"] == "Test Recipe"
            assert result["content"] == "Recipe content"

    @pytest.mark.asyncio
    async def test_get_document_returns_error_for_missing(self):
        """Test that get_document returns error string for missing documents."""
        with patch("agent.tools.db_utils.get_document", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            input_model = tools.DocumentInput(document_id=str(uuid4()))
            result = await tools.get_document_tool(input_model)

            assert isinstance(result, str)
            assert "not found" in result


@pytest.mark.unit
class TestListDocuments:
    """Tests for list documents tool."""

    @pytest.mark.asyncio
    async def test_list_documents_returns_metadata(self):
        """Test that list_documents returns DocumentMetadata models."""
        mock_docs = [
            {
                "id": str(uuid4()),
                "title": f"Recipe {i}",
                "source": f"Recipe {i}.md",
                "metadata": {"cuisine": "Test"},
                "chunk_count": 3,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
            for i in range(1, 4)
        ]

        with patch("agent.tools.db_utils.list_documents", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_docs

            input_model = tools.DocumentListInput()
            results = await tools.list_documents_tool(input_model)

            assert len(results) == 3
            assert results[0].title == "Recipe 1"
            assert results[2].title == "Recipe 3"


@pytest.mark.unit
class TestEntityRelations:
    """Tests for entity relations tool."""

    @pytest.mark.asyncio
    async def test_get_entity_relations_returns_relationships(self):
        """Test that entity_relationship_tool returns relationship data."""
        mock_relations = [
            {
                "fact": "Tacos al Pastor uses cilantro",
                "uuid": str(uuid4()),
            }
        ]

        with patch(
            "agent.tools.graph_utils.get_entity_relationships", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_relations

            input_model = tools.EntityRelationshipInput(entity_name="cilantro")
            results = await tools.entity_relationship_tool(input_model)

            assert len(results) == 1
            assert "cilantro" in results[0]["fact"]
