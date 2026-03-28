"""Neo4j/Graphiti knowledge graph utilities."""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder import OpenAIEmbedder
from graphiti_core.embedder.openai import OpenAIEmbedderConfig
from neo4j import AsyncGraphDatabase

load_dotenv()

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Manages the Graphiti client and Neo4j driver."""

    def __init__(self):
        self._graphiti: Graphiti | None = None
        self._neo4j_driver = None

    async def initialize(self) -> None:
        """Initialize the Graphiti client with LLM and embedder."""
        if self._graphiti is not None:
            return

        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        llm_api_key = os.getenv("LLM_API_KEY", "")

        # Configure LLM client for entity extraction
        llm_config = LLMConfig(
            api_key=llm_api_key,
            model=os.getenv("LLM_CHOICE", "gpt-4.1-mini"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
        llm_client = OpenAIClient(config=llm_config)

        # Configure embedder
        embedder_config = OpenAIEmbedderConfig(
            api_key=os.getenv("EMBEDDING_API_KEY", llm_api_key),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            base_url=os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1"),
        )
        embedder = OpenAIEmbedder(config=embedder_config)

        self._graphiti = Graphiti(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            llm_client=llm_client,
            embedder=embedder,
        )
        await self._graphiti.build_indices_and_constraints()
        logger.info("Graphiti client initialized")

    async def close(self) -> None:
        """Close the Graphiti client and Neo4j driver."""
        if self._graphiti is not None:
            await self._graphiti.close()
            self._graphiti = None
        if self._neo4j_driver is not None:
            await self._neo4j_driver.close()
            self._neo4j_driver = None
        logger.info("Graph clients closed")

    async def _get_neo4j_driver(self):
        """Get or create a direct Neo4j driver."""
        if self._neo4j_driver is None:
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "")
            self._neo4j_driver = AsyncGraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
            )
        return self._neo4j_driver

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search the knowledge graph using Graphiti.

        Args:
            query: Natural language query.
            limit: Maximum results to return.

        Returns:
            List of search result dicts.
        """
        if self._graphiti is None:
            await self.initialize()

        try:
            results = await self._graphiti.search(query, num_results=limit)
            return [
                {
                    "fact": r.fact if hasattr(r, "fact") else str(r),
                    "uuid": str(r.uuid) if hasattr(r, "uuid") else None,
                    "valid_at": str(r.valid_at) if hasattr(r, "valid_at") and r.valid_at else None,
                    "invalid_at": (
                        str(r.invalid_at)
                        if hasattr(r, "invalid_at") and r.invalid_at
                        else None
                    ),
                    "source_node_uuid": (
                        str(r.source_node_uuid)
                        if hasattr(r, "source_node_uuid") and r.source_node_uuid
                        else None
                    ),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Graph search error: {e}")
            return []

    async def get_related_entities(
        self,
        entity_name: str,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """Get entities related to a given entity.

        Args:
            entity_name: Name of the entity.
            depth: Search depth.

        Returns:
            List of related entities and relationships.
        """
        if self._graphiti is None:
            await self.initialize()

        try:
            results = await self._graphiti.search(
                f"relationships of {entity_name}",
                num_results=20,
            )
            return [
                {
                    "fact": r.fact if hasattr(r, "fact") else str(r),
                    "uuid": str(r.uuid) if hasattr(r, "uuid") else None,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Get related entities error: {e}")
            return []

    async def get_entity_timeline(
        self,
        entity_name: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get temporal facts about an entity.

        Args:
            entity_name: Name of the entity.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            List of temporal facts.
        """
        if self._graphiti is None:
            await self.initialize()

        try:
            query = f"timeline of {entity_name}"
            results = await self._graphiti.search(query, num_results=20)
            return [
                {
                    "fact": r.fact if hasattr(r, "fact") else str(r),
                    "valid_at": str(r.valid_at) if hasattr(r, "valid_at") and r.valid_at else None,
                    "invalid_at": (
                        str(r.invalid_at)
                        if hasattr(r, "invalid_at") and r.invalid_at
                        else None
                    ),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Get entity timeline error: {e}")
            return []

    async def get_graph_statistics(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph.

        Returns:
            Dict with node/relationship counts.
        """
        driver = await self._get_neo4j_driver()
        try:
            async with driver.session() as session:
                node_result = await session.run("MATCH (n) RETURN count(n) as count")
                node_count = (await node_result.single())["count"]

                rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = (await rel_result.single())["count"]

                return {
                    "node_count": node_count,
                    "relationship_count": rel_count,
                }
        except Exception as e:
            logger.error(f"Get graph statistics error: {e}")
            return {"node_count": 0, "relationship_count": 0}

    async def clear_graph(self) -> bool:
        """Clear all nodes and relationships from the graph.

        Returns:
            True if successful.
        """
        driver = await self._get_neo4j_driver()
        try:
            async with driver.session() as session:
                await session.run("MATCH (n) DETACH DELETE n")
            return True
        except Exception as e:
            logger.error(f"Clear graph error: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test if Neo4j is accessible.

        Returns:
            True if Neo4j is healthy.
        """
        try:
            driver = await self._get_neo4j_driver()
            async with driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False


# Global client instance
graph_client = GraphitiClient()


# =============================================================================
# Module-level wrapper functions
# =============================================================================


async def initialize_graph() -> None:
    """Initialize the graph client."""
    await graph_client.initialize()


async def close_graph() -> None:
    """Close the graph client."""
    await graph_client.close()


async def get_graphiti_client() -> Graphiti:
    """Get the initialized raw Graphiti client instance.

    Returns:
        The underlying Graphiti client, initialized if needed.
    """
    await graph_client.initialize()
    return graph_client._graphiti


async def search_knowledge_graph(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search the knowledge graph."""
    return await graph_client.search(query, limit=limit)


async def get_entity_relationships(
    entity_name: str,
    depth: int = 1,
) -> list[dict[str, Any]]:
    """Get relationships for an entity."""
    return await graph_client.get_related_entities(entity_name, depth=depth)


async def get_entity_timeline(
    entity_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Get timeline for an entity."""
    return await graph_client.get_entity_timeline(entity_name, start_date, end_date)


async def test_graph_connection() -> bool:
    """Test graph database connection."""
    return await graph_client.test_connection()
