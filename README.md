# Recipe RAG Knowledge Graph

An AI-powered recipe assistant that combines vector search with a knowledge graph to answer natural language questions about recipes, ingredients, cuisines, and cooking techniques.

## Features

- **Hybrid Search**: Combines semantic vector search with knowledge graph queries
- **Recipe Knowledge Graph**: Explore relationships between recipes, ingredients, cuisines, and techniques
- **Streaming Chat**: Real-time responses with tool usage visibility
- **Multi-Cuisine Support**: Mexican, Italian, Chinese, and American Comfort recipes

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Neo4j Desktop](https://neo4j.com/download/) (free, local installation)
- [Neon](https://neon.tech/) PostgreSQL account (free tier available)
- OpenAI API key

## Quick Start

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd recipe-rag-knowledge-graph

# Install dependencies with uv
uv sync

# Install dev dependencies
uv sync --extra dev
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
```

Required environment variables:
- `DATABASE_URL`: Your Neon PostgreSQL connection string
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j Desktop connection
- `LLM_API_KEY`: Your OpenAI API key

### 3. Set Up Databases

#### PostgreSQL (Neon)

1. Create a free account at [neon.tech](https://neon.tech)
2. Create a new project and database
3. Copy the connection string to `DATABASE_URL` in `.env`
4. Run the schema:

```bash
# Using psql
psql $DATABASE_URL -f sql/schema.sql

# Or use Neon's SQL editor to run sql/schema.sql
```

#### Neo4j Desktop

1. Download and install [Neo4j Desktop](https://neo4j.com/download/)
2. Create a new project and database
3. Start the database
4. Update `.env` with your Neo4j credentials:
   - `NEO4J_URI=bolt://localhost:7687`
   - `NEO4J_USER=neo4j`
   - `NEO4J_PASSWORD=<your-password>`

### 4. Ingest Recipe Data

```bash
# Run the ingestion pipeline
uv run python -m ingestion.ingest

# With verbose output
uv run python -m ingestion.ingest --verbose

# Clean and re-ingest
uv run python -m ingestion.ingest --clean
```

### 5. Start the API Server

```bash
uv run python -m agent.api
```

The API will be available at `http://localhost:8058`.

### 6. Use the CLI Client

```bash
# In a new terminal
uv run python cli.py
```

## Project Structure

```
recipe-rag-knowledge-graph/
├── agent/              # AI agent and API
│   ├── agent.py        # Pydantic AI agent
│   ├── api.py          # FastAPI application
│   ├── db_utils.py     # PostgreSQL utilities
│   ├── graph_utils.py  # Neo4j utilities
│   ├── models.py       # Pydantic models
│   ├── prompts.py      # System prompts
│   ├── providers.py    # LLM client factories
│   └── tools.py        # Agent tools
├── ingestion/          # Data ingestion pipeline
│   ├── chunker.py      # Text chunking
│   ├── embedder.py     # Embedding generation
│   ├── graph_builder.py # Knowledge graph construction
│   └── ingest.py       # Pipeline orchestrator
├── recipe_docs/        # Source recipe files (20 recipes)
├── documents/          # Working directory for ingestion
├── sql/
│   └── schema.sql      # PostgreSQL schema
├── tests/              # Test suite
├── cli.py              # Interactive CLI client
├── pyproject.toml      # Project configuration
└── .env.example        # Environment template
```

## Usage Examples

### CLI Commands

```
> What Mexican recipes use cilantro?
> Compare Italian and Chinese pasta dishes
> What are the key ingredients in Mole Poblano?
> Suggest a comfort food recipe for a cold day
> health  # Check API health
> clear   # Clear conversation
> exit    # Exit CLI
```

### API Endpoints

- `GET /health` - Health check
- `POST /chat/stream` - Streaming chat (SSE)

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=agent --cov=ingestion

# Run only unit tests
uv run pytest -m unit

# Run only integration tests (requires databases)
uv run pytest -m integration
```

### Code Formatting

```bash
# Format code
uv run black .

# Check linting
uv run ruff check .

# Fix linting issues
uv run ruff check --fix .
```

## Architecture

The system uses a hybrid approach combining:

1. **Vector Search** (PostgreSQL + pgvector): Semantic similarity search over recipe content using embeddings
2. **Knowledge Graph** (Neo4j + Graphiti): Relationship-based queries for exploring connections between recipes, ingredients, cuisines, and techniques

The AI agent (Pydantic AI) automatically selects the appropriate search strategy based on query intent.

## License

MIT
