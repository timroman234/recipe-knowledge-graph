"""FastAPI application for the Recipe RAG agent."""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from pydantic_ai.messages import (
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPart,
)
from sse_starlette.sse import EventSourceResponse

from agent import db_utils, graph_utils
from agent.agent import AgentDependencies, rag_agent
from agent.models import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthStatus,
    SearchRequest,
    ToolCall,
)
from agent.tools import generate_embedding

load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    logger.info("Starting Recipe RAG Knowledge Graph API...")

    # Initialize database
    try:
        await db_utils.initialize_database()
        db_ok = await db_utils.test_connection()
        logger.info(f"Database connection: {'OK' if db_ok else 'FAILED'}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize graph
    try:
        await graph_utils.initialize_graph()
        graph_ok = await graph_utils.test_graph_connection()
        logger.info(f"Graph database connection: {'OK' if graph_ok else 'FAILED'}")
    except Exception as e:
        logger.error(f"Graph initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await db_utils.close_database()
    await graph_utils.close_graph()


# =============================================================================
# Application Setup
# =============================================================================

app = FastAPI(
    title="Recipe RAG Knowledge Graph API",
    description="AI agent combining vector search and knowledge graph for recipe queries",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Helper Functions
# =============================================================================


async def get_or_create_session(
    session_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Get existing session or create a new one.

    Args:
        session_id: Optional existing session ID.
        user_id: Optional user ID for new sessions.

    Returns:
        Session ID string.
    """
    if session_id:
        session = await db_utils.get_session(session_id)
        if session:
            return session_id

    return await db_utils.create_session(user_id=user_id)


async def get_conversation_context(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Build conversation context from database messages.

    Args:
        session_id: Session ID to load messages for.
        limit: Maximum messages to load.

    Returns:
        List of message dicts.
    """
    return await db_utils.get_session_messages(session_id, limit=limit)


def extract_tool_calls(result) -> list[ToolCall]:
    """Extract tool calls from a pydantic-ai result.

    Args:
        result: Pydantic-ai run result.

    Returns:
        List of ToolCall models.
    """
    tool_calls: list[ToolCall] = []
    try:
        for msg in result.all_messages():
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        args = part.args_as_dict() if hasattr(part, "args_as_dict") else {}
                        tool_calls.append(
                            ToolCall(
                                tool_name=part.tool_name,
                                args=args,
                                tool_call_id=(
                                    part.tool_call_id
                                    if hasattr(part, "tool_call_id")
                                    else None
                                ),
                            )
                        )
    except Exception as e:
        logger.warning(f"Error extracting tool calls: {e}")
    return tool_calls


async def save_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
    tools_used: list[ToolCall] | None = None,
) -> None:
    """Save a conversation turn to the database.

    Args:
        session_id: Session ID.
        user_message: The user's message.
        assistant_message: The assistant's response.
        tools_used: Optional list of tools used.
    """
    try:
        await db_utils.add_message(session_id, "user", user_message)
        metadata = {}
        if tools_used:
            metadata["tools_used"] = [t.model_dump() for t in tools_used]
        await db_utils.add_message(session_id, "assistant", assistant_message, metadata=metadata)
    except Exception as e:
        logger.error(f"Error saving conversation turn: {e}")


async def execute_agent(
    message: str,
    session_id: str,
    user_id: str | None = None,
) -> tuple[str, list[ToolCall]]:
    """Execute the agent with conversation context.

    Args:
        message: User message.
        session_id: Session ID.
        user_id: Optional user ID.

    Returns:
        Tuple of (response text, tools used).
    """
    # Load conversation context
    context = await get_conversation_context(session_id)

    # Build message history for the agent
    message_history = []
    for msg in context:
        from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

        if msg["role"] == "user":
            message_history.append(
                ModelRequest(parts=[UserPromptPart(content=msg["content"])])
            )
        elif msg["role"] == "assistant":
            message_history.append(
                ModelResponse(parts=[TextPart(content=msg["content"])])
            )

    deps = AgentDependencies(session_id=session_id, user_id=user_id)
    result = await rag_agent.run(message, deps=deps, message_history=message_history)

    response_text = result.data
    tool_calls = extract_tool_calls(result)

    # Save conversation turn
    await save_conversation_turn(session_id, message, response_text, tool_calls)

    return response_text, tool_calls


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Check API and database health."""
    db_ok = await db_utils.test_connection()
    graph_ok = await graph_utils.test_graph_connection()

    # Test LLM connection
    llm_ok = True
    try:
        from agent.providers import get_llm_model
        get_llm_model()
    except Exception:
        llm_ok = False

    status = "healthy" if (db_ok and graph_ok) else "degraded"

    return HealthStatus(
        status=status,
        database=db_ok,
        graph_database=graph_ok,
        llm_connection=llm_ok,
        timestamp=datetime.now(timezone.utc),
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat responses using SSE with agent.iter().

    Args:
        request: Chat request with message and optional session_id.

    Returns:
        Streaming response with server-sent events.
    """
    session_id = await get_or_create_session(
        session_id=str(request.session_id) if request.session_id else None,
        user_id=request.user_id,
    )

    async def generate_stream() -> AsyncIterator[str]:
        deps = AgentDependencies(session_id=session_id, user_id=request.user_id)
        full_response = ""

        try:
            # Send session ID first
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            # Load conversation context and build prompt
            context = await get_conversation_context(session_id)
            full_prompt = request.message
            if context:
                context_str = "\n".join(
                    f"{msg['role']}: {msg['content']}" for msg in context[-6:]
                )
                full_prompt = (
                    f"Previous conversation:\n{context_str}\n\n"
                    f"Current question: {request.message}"
                )

            # Stream using agent.iter() pattern
            async with rag_agent.iter(full_prompt, deps=deps) as run:
                async for node in run:
                    if rag_agent.is_model_request_node(node):
                        async with node.stream(run.ctx) as request_stream:
                            async for event in request_stream:
                                if (
                                    isinstance(event, PartStartEvent)
                                    and hasattr(event.part, "content")
                                    and event.part.part_kind == "text"
                                ):
                                    delta = event.part.content
                                    if delta:
                                        full_response += delta
                                        yield f"data: {json.dumps({'type': 'text', 'content': delta})}\n\n"
                                elif (
                                    isinstance(event, PartDeltaEvent)
                                    and isinstance(event.delta, TextPartDelta)
                                ):
                                    delta = event.delta.content_delta
                                    if delta:
                                        full_response += delta
                                        yield f"data: {json.dumps({'type': 'text', 'content': delta})}\n\n"

            # Extract tool calls from final result
            tools_used = extract_tool_calls(run.result)

            # Send tools used
            if tools_used:
                tools_data = [t.model_dump() for t in tools_used]
                yield f"data: {json.dumps({'type': 'tools', 'tools': tools_data})}\n\n"

            # Save conversation
            await save_conversation_turn(
                session_id, request.message, full_response, tools_used
            )

            # Send completion
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        except Exception as e:
            logger.error(f"Error in chat stream: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Non-streaming chat endpoint.

    Args:
        request: Chat request with message and optional session_id.

    Returns:
        Complete response with tools used.
    """
    session_id = await get_or_create_session(
        session_id=str(request.session_id) if request.session_id else None,
        user_id=request.user_id,
    )

    try:
        response_text, tool_calls = await execute_agent(
            message=request.message,
            session_id=session_id,
            user_id=request.user_id,
        )
        return ChatResponse(
            message=response_text,
            session_id=session_id,
            tools_used=tool_calls,
        )
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Search Endpoints
# =============================================================================


class VectorSearchRequest(BaseModel):
    """Request for vector search endpoint."""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50)


class GraphSearchRequest(BaseModel):
    """Request for graph search endpoint."""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50)


class HybridSearchRequest(BaseModel):
    """Request for hybrid search endpoint."""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50)
    text_weight: float = Field(0.3, ge=0.0, le=1.0)


@app.post("/search/vector")
async def search_vector(request: VectorSearchRequest) -> dict:
    """Vector similarity search endpoint."""
    try:
        embedding = await generate_embedding(request.query)
        results = await db_utils.vector_search(embedding, limit=request.limit)
        return {"results": results, "query": request.query, "total": len(results)}
    except Exception as e:
        logger.error(f"Vector search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/graph")
async def search_graph(request: GraphSearchRequest) -> dict:
    """Knowledge graph search endpoint."""
    try:
        results = await graph_utils.search_knowledge_graph(request.query, limit=request.limit)
        return {"results": results, "query": request.query, "total": len(results)}
    except Exception as e:
        logger.error(f"Graph search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/hybrid")
async def search_hybrid(request: HybridSearchRequest) -> dict:
    """Hybrid search endpoint."""
    try:
        embedding = await generate_embedding(request.query)
        results = await db_utils.hybrid_search(
            embedding, request.query, limit=request.limit, text_weight=request.text_weight
        )
        return {"results": results, "query": request.query, "total": len(results)}
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Document Endpoints
# =============================================================================


@app.get("/documents")
async def list_documents(limit: int = 100, offset: int = 0) -> dict:
    """List all available documents."""
    try:
        results = await db_utils.list_documents(limit=limit, offset=offset)
        return {"documents": results, "total": len(results)}
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{document_id}")
async def get_document(document_id: str) -> dict:
    """Get a specific document by ID."""
    result = await db_utils.get_document(document_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")
    return result


# =============================================================================
# Session Endpoints
# =============================================================================


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get session details with messages."""
    session = await db_utils.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    messages = await db_utils.get_session_messages(session_id)
    return {**session, "messages": messages}


# =============================================================================
# Server Runner
# =============================================================================


def run_api() -> None:
    """Run the API server."""
    import uvicorn

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8058"))

    uvicorn.run(
        "agent.api:app",
        host=host,
        port=port,
        reload=os.getenv("APP_ENV") == "development",
    )


if __name__ == "__main__":
    run_api()
