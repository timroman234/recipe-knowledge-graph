"""Tool implementations for the Recipe RAG agent."""

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

from agent import db_utils, graph_utils
from agent.models import ChunkResult, DocumentMetadata, GraphSearchResult
from agent.providers import get_embedding_client, get_embedding_model

logger = logging.getLogger(__name__)

# Module-level embedding client and model
embedding_client = get_embedding_client()
EMBEDDING_MODEL = get_embedding_model()


# =============================================================================
# Embedding Generation
# =============================================================================


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding for the given text.

    Args:
        text: Text to embed.

    Returns:
        Embedding vector as list of floats.
    """
    response = await embedding_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding


# =============================================================================
# Tool Input Models
# =============================================================================


class VectorSearchInput(BaseModel):
    """Input for vector search tool."""

    query: str = Field(..., description="Search query text")
    limit: int = Field(5, ge=1, le=20, description="Maximum results to return")


class GraphSearchInput(BaseModel):
    """Input for graph search tool."""

    query: str = Field(..., description="Search query for knowledge graph")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")


class HybridSearchInput(BaseModel):
    """Input for hybrid search tool."""

    query: str = Field(..., description="Search query text")
    limit: int = Field(10, ge=1, le=20, description="Maximum results to return")
    text_weight: float = Field(0.3, ge=0.0, le=1.0, description="Weight for text search")


class DocumentInput(BaseModel):
    """Input for get document tool."""

    document_id: str = Field(..., description="UUID of the document to retrieve")


class DocumentListInput(BaseModel):
    """Input for list documents tool."""

    limit: int = Field(100, ge=1, le=500, description="Maximum documents to return")
    offset: int = Field(0, ge=0, description="Number of documents to skip")


class EntityRelationshipInput(BaseModel):
    """Input for entity relationship tool."""

    entity_name: str = Field(..., description="Name of the entity")
    depth: int = Field(1, ge=1, le=3, description="Search depth")


class EntityTimelineInput(BaseModel):
    """Input for entity timeline tool."""

    entity_name: str = Field(..., description="Name of the entity")
    start_date: str | None = Field(None, description="Optional start date")
    end_date: str | None = Field(None, description="Optional end date")



# =============================================================================
# Tool Implementations
# =============================================================================


async def vector_search_tool(input: VectorSearchInput) -> list[ChunkResult]:
    """Search for recipes using vector similarity.

    Args:
        input: Vector search input with query and limit.

    Returns:
        List of matching ChunkResult models.
    """
    embedding = await generate_embedding(input.query)
    results = await db_utils.vector_search(embedding, limit=input.limit)

    return [
        ChunkResult(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            document_title=r["document_title"],
            document_source=r["document_source"],
            content=r["content"],
            chunk_index=r["chunk_index"],
            metadata=r.get("metadata", {}),
            score=r["score"],
        )
        for r in results
    ]


async def graph_search_tool(input: GraphSearchInput) -> list[GraphSearchResult]:
    """Search the knowledge graph for recipe relationships.

    Args:
        input: Graph search input with query and limit.

    Returns:
        List of matching GraphSearchResult models.
    """
    results = await graph_utils.search_knowledge_graph(input.query, limit=input.limit)

    return [
        GraphSearchResult(
            fact=r.get("fact", ""),
            uuid=r.get("uuid"),
            valid_at=r.get("valid_at"),
            invalid_at=r.get("invalid_at"),
            source_node_uuid=r.get("source_node_uuid"),
        )
        for r in results
    ]


async def hybrid_search_tool(input: HybridSearchInput) -> list[ChunkResult]:
    """Perform combined vector and graph search.

    Args:
        input: Hybrid search input with query, limit, and text_weight.

    Returns:
        List of matching ChunkResult models.
    """
    embedding = await generate_embedding(input.query)
    results = await db_utils.hybrid_search(
        embedding,
        input.query,
        limit=input.limit,
        text_weight=input.text_weight,
    )

    return [
        ChunkResult(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            document_title=r["document_title"],
            document_source=r["document_source"],
            content=r["content"],
            chunk_index=r["chunk_index"],
            metadata=r.get("metadata", {}),
            score=r["score"],
        )
        for r in results
    ]


async def get_document_tool(input: DocumentInput) -> dict[str, Any] | str:
    """Retrieve a complete recipe document.

    Args:
        input: Document input with document_id.

    Returns:
        Document dict or error string.
    """
    result = await db_utils.get_document(input.document_id)
    if result is None:
        return f"Document with ID '{input.document_id}' not found"
    return result


async def list_documents_tool(input: DocumentListInput) -> list[DocumentMetadata]:
    """List all available recipe documents.

    Args:
        input: List input with limit and offset.

    Returns:
        List of DocumentMetadata models.
    """
    results = await db_utils.list_documents(limit=input.limit, offset=input.offset)

    return [
        DocumentMetadata(
            id=r["id"],
            title=r["title"],
            source=r["source"],
            chunk_count=r.get("chunk_count", 0),
            metadata=r.get("metadata", {}),
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at"),
        )
        for r in results
    ]


async def entity_relationship_tool(
    input: EntityRelationshipInput,
) -> list[dict[str, Any]]:
    """Get relationships for a specific entity.

    Args:
        input: Entity relationship input with entity_name and depth.

    Returns:
        List of relationship dicts.
    """
    return await graph_utils.get_entity_relationships(input.entity_name, depth=input.depth)


async def entity_timeline_tool(input: EntityTimelineInput) -> list[dict[str, Any]]:
    """Get temporal events related to an entity.

    Args:
        input: Entity timeline input.

    Returns:
        List of temporal event dicts.
    """
    return await graph_utils.get_entity_timeline(
        input.entity_name,
        start_date=input.start_date,
        end_date=input.end_date,
    )


async def perform_comprehensive_search(
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Run vector and graph search in parallel for comprehensive results.

    Args:
        query: Search query text.
        limit: Maximum results per search type.

    Returns:
        Combined results from both search methods.
    """
    embedding = await generate_embedding(query)

    vector_task = db_utils.vector_search(embedding, limit=limit)
    graph_task = graph_utils.search_knowledge_graph(query, limit=limit)

    vector_results, graph_results = await asyncio.gather(vector_task, graph_task)

    return {
        "vector_results": vector_results,
        "graph_results": graph_results,
        "total_vector": len(vector_results),
        "total_graph": len(graph_results),
    }


