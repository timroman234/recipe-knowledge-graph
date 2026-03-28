"""Shared pytest fixtures for the Recipe RAG Knowledge Graph tests."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_recipe_metadata() -> dict[str, Any]:
    """Sample recipe metadata for testing."""
    return {
        "title": "Test Tacos",
        "cuisine": "Mexican",
        "servings": 4,
        "prep_time": "20 minutes",
        "cook_time": "15 minutes",
        "ingredients": [
            {"name": "corn tortillas", "amount": "8"},
            {"name": "pork shoulder", "amount": "1 lb"},
            {"name": "pineapple", "amount": "1/2 cup"},
            {"name": "onion", "amount": "1"},
            {"name": "cilantro", "amount": "1/4 cup"},
        ],
        "techniques": ["marinating", "grilling", "dicing"],
        "equipment": ["grill", "cutting board", "chef's knife"],
    }


@pytest.fixture
def sample_recipe_content() -> str:
    """Sample recipe content for testing."""
    return """---
title: Test Tacos
cuisine: Mexican
servings: 4
prep_time: 20 minutes
cook_time: 15 minutes
ingredients:
  - name: corn tortillas
    amount: "8"
  - name: pork shoulder
    amount: 1 lb
---

# Test Tacos

A delicious test recipe for tacos.

## Ingredients

- 8 corn tortillas
- 1 lb pork shoulder
- 1/2 cup pineapple

## Instructions

1. Marinate the pork
2. Grill until cooked
3. Slice and serve in tortillas
"""


@pytest.fixture
def sample_chunks() -> list[dict[str, Any]]:
    """Sample chunks for testing."""
    return [
        {
            "content": "## Test Tacos\n\nA delicious test recipe for tacos.",
            "chunk_index": 0,
            "metadata": {"section": "Introduction", "cuisine": "Mexican"},
        },
        {
            "content": "## Ingredients\n\n- 8 corn tortillas\n- 1 lb pork shoulder",
            "chunk_index": 1,
            "metadata": {"section": "Ingredients", "cuisine": "Mexican"},
        },
        {
            "content": "## Instructions\n\n1. Marinate the pork\n2. Grill until cooked",
            "chunk_index": 2,
            "metadata": {"section": "Instructions", "cuisine": "Mexican"},
        },
    ]


@pytest.fixture
def sample_embedding() -> list[float]:
    """Sample embedding vector for testing (1536 dimensions)."""
    return [0.01] * 1536


@pytest.fixture
def sample_document_id():
    """Sample document UUID."""
    return uuid4()


@pytest.fixture
def sample_session_id():
    """Sample session UUID."""
    return uuid4()


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for LLM and embeddings."""
    client = AsyncMock()

    # Mock embedding response
    embedding_response = MagicMock()
    embedding_data = MagicMock()
    embedding_data.embedding = [0.01] * 1536
    embedding_response.data = [embedding_data]
    client.embeddings.create.return_value = embedding_response

    # Mock chat completion response
    chat_response = MagicMock()
    choice = MagicMock()
    choice.message.content = "This is a test response about recipes."
    chat_response.choices = [choice]
    client.chat.completions.create.return_value = chat_response

    return client


@pytest.fixture
def mock_graphiti_client():
    """Mock Graphiti client for knowledge graph."""
    client = AsyncMock()

    # Mock search results
    search_result = MagicMock()
    search_result.fact = "Test recipe uses cilantro"
    search_result.uuid = uuid4()
    search_result.valid_at = None
    search_result.invalid_at = None
    search_result.source_node_uuid = None
    search_result.score = 0.95
    client.search.return_value = [search_result]

    # Mock add_episode
    episode = MagicMock()
    episode.uuid = uuid4()
    client.add_episode.return_value = episode

    return client


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for graph queries."""
    driver = AsyncMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__.return_value = session

    # Mock query results
    result = AsyncMock()
    result.data.return_value = [
        {
            "source": "Tacos al Pastor",
            "relationship": "USES_INGREDIENT",
            "target": "cilantro",
            "properties": {},
        }
    ]
    session.run.return_value = result

    return driver


# =============================================================================
# Integration Test Markers
# =============================================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests with mocked dependencies")
    config.addinivalue_line("markers", "integration: Integration tests requiring databases")
