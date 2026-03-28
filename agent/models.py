"""Pydantic models for the Recipe RAG Knowledge Graph agent."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class SearchType(str, Enum):
    """Type of search to perform."""

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


# =============================================================================
# Request Models
# =============================================================================


class ChatRequest(BaseModel):
    """Request for chat endpoint."""

    message: str = Field(..., description="User message")
    session_id: UUID | None = Field(None, description="Session ID for conversation continuity")
    user_id: str | None = Field(None, description="User ID for session tracking")
    metadata: dict[str, Any] | None = Field(None, description="Optional request metadata")
    search_type: SearchType | None = Field(None, description="Preferred search type")


class SearchRequest(BaseModel):
    """Request for search endpoint."""

    query: str = Field(..., description="Search query")
    search_type: SearchType = Field(SearchType.HYBRID, description="Type of search")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")


# =============================================================================
# Response Models
# =============================================================================


class ChunkResult(BaseModel):
    """A single chunk result from vector search."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_source: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float


class GraphSearchResult(BaseModel):
    """A single result from knowledge graph search."""

    fact: str
    uuid: str | None = None
    valid_at: str | None = None
    invalid_at: str | None = None
    source_node_uuid: str | None = None


class ToolCall(BaseModel):
    """A tool call made by the agent."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    tool_call_id: str | None = None


class DocumentMetadata(BaseModel):
    """Metadata for a document."""

    id: UUID
    title: str
    source: str
    chunk_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SearchResponse(BaseModel):
    """Response from search endpoint."""

    results: list[ChunkResult | GraphSearchResult]
    search_type: SearchType
    query: str
    total_results: int


class ChatResponse(BaseModel):
    """Response from chat endpoint (non-streaming)."""

    message: str
    session_id: UUID
    tools_used: list[ToolCall] = Field(default_factory=list)


class StreamDelta(BaseModel):
    """A single delta in a streaming response."""

    type: str = Field(..., description="Type: 'text', 'tool_start', 'tool_end', 'error'")
    content: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: str | None = None


# =============================================================================
# Database Models
# =============================================================================


class Document(BaseModel):
    """A document (recipe) in the database."""

    id: UUID
    title: str
    source: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class Chunk(BaseModel):
    """A text chunk with embedding."""

    id: UUID
    document_id: UUID
    content: str
    chunk_index: int
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class Session(BaseModel):
    """A conversation session."""

    id: UUID
    user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None


class Message(BaseModel):
    """A message in a conversation."""

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# =============================================================================
# Agent Models
# =============================================================================


class AgentDependencies(BaseModel):
    """Dependencies for the recipe agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str | None = None
    user_id: str | None = None
    search_preferences: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Ingestion Models
# =============================================================================


class IngestionConfig(BaseModel):
    """Configuration for document ingestion."""

    chunk_size: int = Field(800, description="Target chunk size in characters")
    chunk_overlap: int = Field(150, description="Overlap between chunks")
    max_chunk_size: int = Field(1500, description="Maximum chunk size")
    batch_size: int = Field(10, description="Batch size for embedding generation")


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    document_id: UUID
    document_name: str
    chunks_created: int
    graph_entities_created: int
    success: bool
    error: str | None = None
    processing_time_ms: float | None = None
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# Utility Models
# =============================================================================


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str | None = None
    code: str | None = None
    error_type: str | None = None
    request_id: str | None = None


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = "healthy"
    database: bool = False
    graph_database: bool = False
    llm_connection: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "0.1.0"
