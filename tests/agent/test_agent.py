"""Tests for the Recipe RAG agent."""

import pytest
from unittest.mock import patch

from agent.agent import AgentDependencies, rag_agent


@pytest.mark.unit
class TestAgentCreation:
    """Tests for agent creation and configuration."""

    def test_rag_agent_exists(self):
        """Test that the module-level rag_agent is created."""
        assert rag_agent is not None

    def test_agent_dependencies_dataclass(self):
        """Test AgentDependencies dataclass."""
        deps = AgentDependencies(
            session_id="test-session",
            user_id="test-user",
        )

        assert deps.session_id == "test-session"
        assert deps.user_id == "test-user"

    def test_agent_dependencies_defaults(self):
        """Test AgentDependencies default values."""
        deps = AgentDependencies()

        assert deps.session_id is None
        assert deps.user_id is None
        assert deps.search_preferences == {}

    def test_agent_dependencies_search_preferences(self):
        """Test AgentDependencies with search preferences."""
        deps = AgentDependencies(
            search_preferences={"type": "vector", "limit": 5},
        )

        assert deps.search_preferences["type"] == "vector"
        assert deps.search_preferences["limit"] == 5


@pytest.mark.unit
class TestAgentToolRegistration:
    """Tests for agent tool registration."""

    def test_agent_has_tools(self):
        """Test that agent has tools registered."""
        # pydantic-ai stores tools internally
        assert hasattr(rag_agent, "_function_tools") or hasattr(rag_agent, "tools")


@pytest.mark.unit
class TestAgentSystemPrompt:
    """Tests for agent system prompt."""

    def test_system_prompt_contains_recipe_context(self):
        """Test that system prompt mentions recipes."""
        from agent.prompts import SYSTEM_PROMPT

        assert "recipe" in SYSTEM_PROMPT.lower()
        assert "ingredient" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_cuisines(self):
        """Test that system prompt mentions supported cuisines."""
        from agent.prompts import SYSTEM_PROMPT

        assert "Mexican" in SYSTEM_PROMPT
        assert "Italian" in SYSTEM_PROMPT
        assert "Chinese" in SYSTEM_PROMPT
        assert "American" in SYSTEM_PROMPT

    def test_system_prompt_describes_tools(self):
        """Test that system prompt describes available tools."""
        from agent.prompts import SYSTEM_PROMPT

        assert "vector" in SYSTEM_PROMPT.lower()
        assert "graph" in SYSTEM_PROMPT.lower()
        assert "hybrid" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_knowledge_graph_guidance(self):
        """Test that system prompt includes tool selection guidance."""
        from agent.prompts import SYSTEM_PROMPT

        assert "knowledge graph" in SYSTEM_PROMPT.lower()
