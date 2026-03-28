"""Pydantic AI agent for recipe queries."""

from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext

from agent import prompts, tools
from agent.providers import get_llm_model


@dataclass
class AgentDependencies:
    """Dependencies injected into the recipe agent."""

    session_id: str | None = None
    user_id: str | None = None
    search_preferences: dict[str, Any] = field(default_factory=dict)


# Create module-level agent instance
rag_agent: Agent[AgentDependencies, str] = Agent(
    get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=prompts.SYSTEM_PROMPT,
)


# =============================================================================
# Tool Registrations
# =============================================================================


@rag_agent.tool
async def vector_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search for recipes using semantic similarity.

    Use this tool when the user asks about recipe content, instructions,
    ingredients, or wants to find recipes similar to a description.

    Args:
        ctx: Run context with agent dependencies.
        query: Natural language search query.
        limit: Maximum number of results (default 5).

    Returns:
        List of relevant recipe chunks with similarity scores.
    """
    input_model = tools.VectorSearchInput(query=query, limit=limit)
    results = await tools.vector_search_tool(input_model)
    return [r.model_dump() for r in results]


@rag_agent.tool
async def graph_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search the knowledge graph for recipe relationships.

    Use this tool when asking about relationships between recipes, ingredients,
    cuisines, and cooking techniques. Best for exploring connections.

    Args:
        ctx: Run context with agent dependencies.
        query: Natural language query about relationships.
        limit: Maximum number of results (default 10).

    Returns:
        List of relevant entities and their relationships.
    """
    input_model = tools.GraphSearchInput(query=query, limit=limit)
    results = await tools.graph_search_tool(input_model)
    return [r.model_dump() for r in results]


@rag_agent.tool
async def hybrid_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Perform combined vector and graph search.

    Use this for comprehensive results from both semantic content
    search and relationship-based graph search.

    Args:
        ctx: Run context with agent dependencies.
        query: Natural language search query.
        limit: Maximum number of results (default 10).

    Returns:
        List of matching recipe chunks with combined scores.
    """
    input_model = tools.HybridSearchInput(query=query, limit=limit)
    results = await tools.hybrid_search_tool(input_model)
    return [r.model_dump() for r in results]


@rag_agent.tool
async def get_document(
    ctx: RunContext[AgentDependencies],
    document_id: str,
) -> dict[str, Any] | str:
    """Retrieve a complete recipe document by its ID.

    Use this when the user wants full details about a specific recipe.

    Args:
        ctx: Run context with agent dependencies.
        document_id: UUID of the recipe document.

    Returns:
        Complete recipe document with all content and metadata.
    """
    input_model = tools.DocumentInput(document_id=document_id)
    return await tools.get_document_tool(input_model)


@rag_agent.tool
async def list_documents(
    ctx: RunContext[AgentDependencies],
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List all available recipes.

    Use this when the user wants to see what recipes are available.

    Args:
        ctx: Run context with agent dependencies.
        limit: Maximum number of documents to return.

    Returns:
        List of all recipe documents with basic metadata.
    """
    input_model = tools.DocumentListInput(limit=limit)
    results = await tools.list_documents_tool(input_model)
    return [r.model_dump() for r in results]


@rag_agent.tool
async def get_entity_relations(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    depth: int = 1,
) -> list[dict[str, Any]]:
    """Get relationships for a specific entity in the knowledge graph.

    Use this to explore all connections for a particular ingredient,
    recipe, technique, or cuisine.

    Args:
        ctx: Run context with agent dependencies.
        entity_name: Name of the entity to explore.
        depth: Search depth (default 1).

    Returns:
        List of relationships connected to the entity.
    """
    input_model = tools.EntityRelationshipInput(entity_name=entity_name, depth=depth)
    return await tools.entity_relationship_tool(input_model)


