"""Knowledge graph construction from recipe metadata."""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class RecipeEntity:
    """Represents an entity extracted from a recipe."""

    name: str
    entity_type: str  # Recipe, Ingredient, Cuisine, Technique, Equipment
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecipeRelation:
    """Represents a relationship between recipe entities."""

    source: str
    relation_type: str  # USES_INGREDIENT, BELONGS_TO_CUISINE, USES_TECHNIQUE, REQUIRES_EQUIPMENT
    target: str
    properties: dict[str, Any] = field(default_factory=dict)


class GraphBuilder:
    """Builds knowledge graph from recipe metadata."""

    def __init__(self):
        """Initialize the graph builder."""
        self._graphiti_client = None

    async def get_graphiti_client(self):
        """Get or create the Graphiti client."""
        if self._graphiti_client is None:
            from agent.graph_utils import get_graphiti_client

            self._graphiti_client = await get_graphiti_client()
        return self._graphiti_client

    def extract_entities(
        self,
        metadata: dict[str, Any],
        recipe_name: str,
    ) -> tuple[list[RecipeEntity], list[RecipeRelation]]:
        """Extract entities and relationships from recipe metadata.

        Args:
            metadata: Recipe frontmatter metadata.
            recipe_name: Name of the recipe.

        Returns:
            Tuple of (entities, relations).
        """
        entities: list[RecipeEntity] = []
        relations: list[RecipeRelation] = []

        # Create recipe entity
        recipe_entity = RecipeEntity(
            name=recipe_name,
            entity_type="Recipe",
            properties={
                "title": metadata.get("title", recipe_name),
                "servings": metadata.get("servings"),
                "prep_time": metadata.get("prep_time"),
                "cook_time": metadata.get("cook_time"),
            },
        )
        entities.append(recipe_entity)

        # Extract cuisine
        cuisine = metadata.get("cuisine")
        if cuisine:
            entities.append(
                RecipeEntity(name=cuisine, entity_type="Cuisine", properties={})
            )
            relations.append(
                RecipeRelation(
                    source=recipe_name,
                    relation_type="BELONGS_TO_CUISINE",
                    target=cuisine,
                )
            )

        # Extract ingredients
        ingredients = metadata.get("key_ingredients", metadata.get("ingredients", []))
        for ingredient in ingredients:
            # Handle both string and dict ingredient formats
            if isinstance(ingredient, dict):
                ing_name = ingredient.get("name", str(ingredient))
                ing_amount = ingredient.get("amount", "")
            else:
                ing_name = str(ingredient)
                ing_amount = ""

            entities.append(
                RecipeEntity(
                    name=ing_name,
                    entity_type="Ingredient",
                    properties={"amount": ing_amount} if ing_amount else {},
                )
            )
            relations.append(
                RecipeRelation(
                    source=recipe_name,
                    relation_type="USES_INGREDIENT",
                    target=ing_name,
                    properties={"amount": ing_amount} if ing_amount else {},
                )
            )

        # Extract techniques
        techniques = metadata.get("cooking_techniques", metadata.get("techniques", []))
        for technique in techniques:
            entities.append(
                RecipeEntity(name=technique, entity_type="Technique", properties={})
            )
            relations.append(
                RecipeRelation(
                    source=recipe_name,
                    relation_type="USES_TECHNIQUE",
                    target=technique,
                )
            )

        # Extract equipment
        equipment = metadata.get("equipment", [])
        for equip in equipment:
            entities.append(
                RecipeEntity(name=equip, entity_type="Equipment", properties={})
            )
            relations.append(
                RecipeRelation(
                    source=recipe_name,
                    relation_type="REQUIRES_EQUIPMENT",
                    target=equip,
                )
            )

        # Extract pairing suggestions
        pairings = metadata.get("pairs_well_with", [])
        for pairing in pairings:
            entities.append(
                RecipeEntity(name=pairing, entity_type="Ingredient", properties={})
            )
            relations.append(
                RecipeRelation(
                    source=recipe_name,
                    relation_type="PAIRS_WELL_WITH",
                    target=pairing,
                )
            )

        return entities, relations

    async def build_recipe_graph(
        self,
        metadata: dict[str, Any],
        recipe_name: str,
        content: str,
    ) -> dict[str, int]:
        """Build knowledge graph nodes and edges for a recipe.

        Args:
            metadata: Recipe frontmatter metadata.
            recipe_name: Name of the recipe.
            content: Full recipe content for context.

        Returns:
            Dict with counts of created entities and relations.
        """
        entities, relations = self.extract_entities(metadata, recipe_name)

        # Add to Graphiti via episode
        await self.add_recipe_to_graph(recipe_name, content, metadata)

        return {
            "entities_created": len(entities),
            "relations_created": len(relations),
        }

    async def add_recipe_to_graph(
        self,
        recipe_name: str,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """Add a recipe to the knowledge graph via Graphiti.

        Args:
            recipe_name: Name of the recipe.
            content: Recipe content.
            metadata: Recipe metadata.

        Returns:
            Episode ID.
        """
        from graphiti_core.nodes import EpisodeType

        client = await self.get_graphiti_client()

        # Create a structured episode from the recipe
        episode_content = self._format_recipe_for_graph(recipe_name, content, metadata)

        try:
            episode = await client.add_episode(
                name=recipe_name,
                episode_body=episode_content,
                source=EpisodeType.text,
                source_description=f"Recipe: {metadata.get('title', recipe_name)} ({metadata.get('cuisine', 'Unknown')} cuisine)",
                reference_time=datetime.now(timezone.utc),
            )
            logger.info(f"Added recipe '{recipe_name}' to knowledge graph")
            return str(episode.uuid) if hasattr(episode, "uuid") else str(episode)
        except Exception as e:
            logger.error(f"Failed to add recipe '{recipe_name}' to graph: {e}")
            raise

    def _format_recipe_for_graph(
        self,
        recipe_name: str,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """Format recipe content for knowledge graph ingestion.

        Args:
            recipe_name: Name of the recipe.
            content: Recipe content.
            metadata: Recipe metadata.

        Returns:
            Formatted string optimized for entity extraction.
        """
        parts = [f"Recipe: {recipe_name}"]

        if metadata.get("cuisine"):
            parts.append(f"Cuisine: {metadata['cuisine']}")

        ingredients = metadata.get("key_ingredients", metadata.get("ingredients"))
        if ingredients:
            if isinstance(ingredients, list):
                ing_str = ", ".join(
                    ing.get("name", str(ing)) if isinstance(ing, dict) else str(ing)
                    for ing in ingredients
                )
                parts.append(f"Ingredients: {ing_str}")

        techniques = metadata.get("cooking_techniques", metadata.get("techniques"))
        if techniques:
            parts.append(f"Techniques: {', '.join(techniques)}")

        if metadata.get("equipment"):
            parts.append(f"Equipment: {', '.join(metadata['equipment'])}")

        # Add a summary of the content
        parts.append(f"\n{content[:1000]}...")  # Truncate for efficiency

        return "\n".join(parts)

    async def close(self) -> None:
        """Close the Graphiti client."""
        if self._graphiti_client is not None:
            await self._graphiti_client.close()
            self._graphiti_client = None


# Module-level convenience function


async def build_recipe_graph(
    metadata: dict[str, Any],
    recipe_name: str,
    content: str,
) -> dict[str, int]:
    """Build knowledge graph for a recipe.

    Args:
        metadata: Recipe frontmatter metadata.
        recipe_name: Name of the recipe.
        content: Full recipe content.

    Returns:
        Dict with counts of created entities and relations.
    """
    builder = GraphBuilder()
    try:
        return await builder.build_recipe_graph(metadata, recipe_name, content)
    finally:
        await builder.close()
