"""LLM and embedding provider factories."""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()


def get_llm_model() -> OpenAIModel:
    """Get the configured LLM model for the agent.

    Returns:
        OpenAIModel configured from environment variables.
    """
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model_name = os.getenv("LLM_CHOICE", "gpt-4.1-mini")

    provider = OpenAIProvider(api_key=api_key, base_url=base_url)
    return OpenAIModel(model_name, provider=provider)


def get_ingestion_model() -> OpenAIModel:
    """Get the configured LLM model for ingestion tasks.

    Uses INGESTION_LLM_CHOICE env var, falling back to a smaller model.

    Returns:
        OpenAIModel configured for ingestion.
    """
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model_name = os.getenv("INGESTION_LLM_CHOICE", "gpt-4.1-nano")

    provider = OpenAIProvider(api_key=api_key, base_url=base_url)
    return OpenAIModel(model_name, provider=provider)


def get_embedding_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client for embedding operations.

    Returns:
        AsyncOpenAI client configured for embeddings.
    """
    api_key = os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY", ""))
    base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")

    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def get_embedding_model() -> str:
    """Get the embedding model name.

    Returns:
        Embedding model name string.
    """
    return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def get_llm_provider() -> str:
    """Get the LLM provider name.

    Returns:
        Provider name (e.g., 'openai').
    """
    return os.getenv("LLM_PROVIDER", "openai")


def get_embedding_provider() -> str:
    """Get the embedding provider name.

    Returns:
        Provider name (e.g., 'openai').
    """
    return os.getenv("EMBEDDING_PROVIDER", "openai")


def get_model_info() -> dict[str, str]:
    """Get information about configured models.

    Returns:
        Dict with model configuration details.
    """
    return {
        "llm_provider": get_llm_provider(),
        "llm_model": os.getenv("LLM_CHOICE", "gpt-4.1-mini"),
        "embedding_provider": get_embedding_provider(),
        "embedding_model": get_embedding_model(),
        "ingestion_model": os.getenv("INGESTION_LLM_CHOICE", "gpt-4.1-nano"),
    }


def validate_configuration() -> list[str]:
    """Validate that all required configuration is present.

    Returns:
        List of validation error messages. Empty list means valid.
    """
    errors: list[str] = []

    if not os.getenv("LLM_API_KEY"):
        errors.append("LLM_API_KEY is not set")

    if not os.getenv("DATABASE_URL"):
        errors.append("DATABASE_URL is not set")

    if not os.getenv("NEO4J_URI"):
        errors.append("NEO4J_URI is not set (using default bolt://localhost:7687)")

    return errors
