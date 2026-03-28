# PLANNING.md

## Project Overview

Recipe RAG Knowledge Graph is an AI-powered recipe assistant that combines vector search (for semantic recipe retrieval) with a knowledge graph (for exploring relationships between recipes, ingredients, cuisines, and cooking techniques).

The system enables natural language queries about recipes, supporting:
- Finding recipes by description or ingredients
- Exploring cuisine relationships
- Comparing cooking techniques across cultures
- Ingredient substitution suggestions
- Recipe recommendations based on context

## Architecture Overview

```
┌──────────────────────────────────┐  ┌────────────────────────────────────┐
│           CLI Client             │  │       Streamlit Frontend           │
│    (cli.py - Interactive REPL)   │  │ (frontend/app.py - Web UI)        │
└───────────────┬──────────────────┘  └──────────────┬─────────────────────┘
                │ HTTP/SSE                           │ HTTP/SSE
                └──────────────┬─────────────────────┘
┌────────────────────────────────▼────────────────────────────────────────┐
│                              API Layer                                   │
│                      (agent/api.py - FastAPI)                            │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │  /health     │    │ /chat/stream │    │  Lifespan Management     │   │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                            Agent Layer                                   │
│                   (agent/agent.py - Pydantic AI)                         │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                         RecipeAgent                              │    │
│  │  - System prompt (recipes, cuisines, techniques)                 │    │
│  │  - Tool orchestration                                            │    │
│  │  - Response streaming                                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                            Tools                                 │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐   │    │
│  │  │ vector_    │ │ graph_     │ │ hybrid_    │ │ get_        │   │    │
│  │  │ search     │ │ search     │ │ search     │ │ document    │   │    │
│  │  └────────────┘ └────────────┘ └────────────┘ └─────────────┘   │    │
│  │  ┌────────────┐ ┌─────────────────┐ ┌────────────────────────┐  │    │
│  │  │ list_      │ │ get_entity_     │ │ get_entity_            │  │    │
│  │  │ documents  │ │ relations       │ │ timeline               │  │    │
│  │  └────────────┘ └─────────────────┘ └────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└───────────────────┬─────────────────────────────┬───────────────────────┘
                    │                             │
┌───────────────────▼───────────────┐ ┌──────────▼────────────────────────┐
│      PostgreSQL + pgvector        │ │         Neo4j Knowledge Graph      │
│         (Neon Database)           │ │          (Neo4j Desktop)           │
│                                   │ │                                    │
│  ┌─────────────────────────────┐  │ │  ┌──────────────────────────────┐ │
│  │ documents                   │  │ │  │ Nodes                        │ │
│  │ - id, name, content         │  │ │  │ - Recipe, Ingredient         │ │
│  │ - metadata (JSONB)          │  │ │  │ - Cuisine, Technique         │ │
│  └─────────────────────────────┘  │ │  │ - Equipment                  │ │
│  ┌─────────────────────────────┐  │ │  └──────────────────────────────┘ │
│  │ chunks                      │  │ │  ┌──────────────────────────────┐ │
│  │ - id, document_id           │  │ │  │ Relationships                │ │
│  │ - content, embedding        │  │ │  │ - USES_INGREDIENT            │ │
│  │ - chunk_index               │  │ │  │ - BELONGS_TO_CUISINE         │ │
│  └─────────────────────────────┘  │ │  │ - USES_TECHNIQUE             │ │
│  ┌─────────────────────────────┐  │ │  │ - REQUIRES_EQUIPMENT         │ │
│  │ sessions, messages          │  │ │  └──────────────────────────────┘ │
│  └─────────────────────────────┘  │ │                                    │
└───────────────────────────────────┘ └────────────────────────────────────┘
                    ▲
                    │ Ingestion
┌───────────────────┴─────────────────────────────────────────────────────┐
│                         Ingestion Pipeline                               │
│                                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────────┐ │
│  │ recipe_docs/ │──▶│   Chunker    │──▶│   Embedder                   │ │
│  │ (20 recipes) │   │ (chunker.py) │   │ (embedder.py)                │ │
│  └──────────────┘   └──────────────┘   └──────────────────────────────┘ │
│                            │                           │                 │
│                            ▼                           ▼                 │
│               ┌──────────────────────┐    ┌──────────────────────────┐  │
│               │    Graph Builder     │    │    PostgreSQL Insert     │  │
│               │  (graph_builder.py)  │    │    (ingest.py)           │  │
│               └──────────────────────┘    └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### agent/
- **models.py**: Pydantic models for requests, responses, database entities
- **providers.py**: LLM and embedding client factories
- **db_utils.py**: PostgreSQL/asyncpg connection pool and CRUD operations
- **graph_utils.py**: Neo4j/Graphiti client and graph query operations
- **prompts.py**: System prompts for the recipe agent
- **tools.py**: Tool implementations (search, retrieval, graph queries)
- **agent.py**: Pydantic AI agent configuration and tool registration
- **api.py**: FastAPI application with streaming chat endpoint

### frontend/
- **app.py**: Main Streamlit application (entry point)
- **config.py**: Frontend configuration (API URL, titles, timeouts)
- **api_client.py**: HTTP/SSE client using httpx for backend communication
- **styles.py**: IBM Carbon-inspired CSS styling
- **components.py**: Reusable UI rendering functions (tool cards, health, empty state)

### ingestion/
- **chunker.py**: Semantic text chunking with YAML frontmatter parsing
- **embedder.py**: OpenAI embedding generation with batching
- **graph_builder.py**: Knowledge graph construction from recipe metadata
- **ingest.py**: Main orchestrator for the ingestion pipeline

### sql/
- **schema.sql**: PostgreSQL schema with pgvector extension

### tests/
- Unit tests with mocked dependencies
- Integration tests for database operations

## Technical Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | Pydantic AI |
| API Framework | FastAPI |
| Vector Database | PostgreSQL + pgvector (Neon) |
| Knowledge Graph | Neo4j (Desktop) + Graphiti |
| LLM Provider | OpenAI (gpt-4.1-mini) |
| Embeddings | OpenAI (text-embedding-3-small) |
| Package Manager | uv |
| Frontend | Streamlit |
| Testing | pytest + pytest-asyncio |

## Design Principles

1. **Hybrid Search**: Combine vector similarity for semantic search with knowledge graph for relationship exploration.
2. **Streaming Responses**: Use SSE for real-time chat responses.
3. **Tool-Based Agent**: Let the LLM choose appropriate tools based on query intent.
4. **Modular Architecture**: Clear separation between API, agent, and ingestion layers.
5. **Type Safety**: Pydantic models for all data structures, type hints throughout.

## Key Features

### Hybrid Search
- **Vector Search**: Semantic similarity using embeddings
- **Graph Search**: Relationship-based queries through knowledge graph
- **Combined**: Unified results from both sources

### Knowledge Graph
- Entities: Recipe, Ingredient, Cuisine, Technique, Equipment
- Relationships: USES_INGREDIENT, BELONGS_TO_CUISINE, USES_TECHNIQUE, REQUIRES_EQUIPMENT
- Enables: "What recipes share ingredients with Tacos al Pastor?"

### Streaming Chat
- SSE-based streaming for responsive UX
- Real-time tool usage visibility
- Session-based conversation history

## Implementation Phases

1. **Phase 0**: Project scaffolding (current)
2. **Phase 1**: Recipe documents (complete - 20 recipes in recipe_docs/)
3. **Phase 2**: Database foundation (PostgreSQL schema, Neo4j setup)
4. **Phase 3**: Ingestion pipeline (chunking, embedding, graph building)
5. **Phase 4**: Agent and tools (Pydantic AI agent with search tools)
6. **Phase 5**: API layer (FastAPI with streaming)
7. **Phase 6**: CLI client (interactive REPL)
8. **Phase 7**: Testing and polish
9. **Phase 8**: Streamlit frontend (IBM Carbon-inspired web UI)

## Configuration

### Environment Variables
See `.env.example` for all configuration options.

Key settings:
- `DATABASE_URL`: Neon PostgreSQL connection string
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j Desktop connection
- `LLM_API_KEY`, `LLM_CHOICE`: OpenAI API configuration
- `EMBEDDING_MODEL`: OpenAI embedding model (text-embedding-3-small)
- `CHUNK_SIZE`, `CHUNK_OVERLAP`: Text chunking parameters
