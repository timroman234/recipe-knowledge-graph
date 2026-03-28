# Product Requirements Document (PRD)
# Recipe RAG Knowledge Graph — Agentic AI Teaching Project

**Version:** 1.0
**Date:** March 25, 2026
**Status:** Ready for Development

---

## 1. Project Overview

### What We're Building

An AI agent that can intelligently search and reason about a collection of food recipes using two complementary search strategies:

- **Vector Search (Agentic RAG):** "Find me chicken recipes" — searches PostgreSQL/pgvector for semantically similar recipe chunks
- **Knowledge Graph Search:** "What recipes share ingredients with Pad Thai?" — traverses a Neo4j graph of relationships between recipes, ingredients, cuisines, and techniques

The agent decides which search strategy to use (or both) based on the user's question. This is what makes it "agentic" — it reasons about tool selection rather than following a fixed pipeline.

### Who This Is For

Developers learning to build AI agents. This project teaches:

1. How the **agent loop** works (LLM reasons → picks a tool → executes → reasons again)
2. How **RAG** (Retrieval Augmented Generation) gives an LLM access to private data
3. How **knowledge graphs** capture relationships that flat vector search misses
4. How **Pydantic AI** structures agents with typed tools and dependency injection
5. How **FastAPI + SSE streaming** delivers real-time agent responses
6. How a **CLI client** consumes a streaming API

### Adapted From

Cole Medin's [ottomator-agents/agentic-rag-knowledge-graph](https://github.com/coleam00/ottomator-agents/tree/main/agentic-rag-knowledge-graph) — originally built for analyzing big tech company documents. We adapt the domain to food recipes, which provides a richer and more intuitive entity-relationship model for teaching knowledge graphs.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     CLI Client (cli.py)                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Interactive REPL with streaming SSE consumption       │  │
│  │  Color-coded output · Tool usage visibility            │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│                         │ HTTP POST + SSE Stream              │
├─────────────────────────┴────────────────────────────────────┤
│                     API Layer (agent/api.py)                  │
│  ┌─────────────────┐        ┌──────────────────────────┐    │
│  │   FastAPI        │        │   SSE Streaming          │    │
│  │   /chat/stream   │        │   Real-time responses    │    │
│  │   /health        │        │   Tool usage events      │    │
│  └────────┬─────────┘        └──────────────────────────┘    │
│           │                                                   │
├───────────┴──────────────────────────────────────────────────┤
│                     Agent Layer (agent/agent.py)              │
│  ┌─────────────────┐        ┌──────────────────────────┐    │
│  │  Pydantic AI     │        │   Agent Tools            │    │
│  │  Agent           │◄──────►│  - vector_search         │    │
│  │  (gpt-4.1-mini)  │        │  - graph_search          │    │
│  │                   │        │  - hybrid_search         │    │
│  │  System prompt    │        │  - get_document          │    │
│  │  tells agent when │        │  - list_documents        │    │
│  │  to use which     │        │  - get_entity_relations  │    │
│  │  tool             │        │  - get_entity_timeline   │    │
│  └────────┬─────────┘        └──────────────────────────┘    │
│           │                                                   │
├───────────┴──────────────────────────────────────────────────┤
│                     Storage Layer                             │
│  ┌─────────────────────────┐  ┌───────────────────────────┐ │
│  │   PostgreSQL (Neon)     │  │   Neo4j Desktop           │ │
│  │   + pgvector            │  │   (via Graphiti library)   │ │
│  │                         │  │                           │ │
│  │   • documents table     │  │   • Recipe nodes          │ │
│  │   • chunks + embeddings │  │   • Ingredient nodes      │ │
│  │   • sessions/messages   │  │   • Cuisine nodes         │ │
│  │   • hybrid_search()     │  │   • Technique edges       │ │
│  │   • match_chunks()      │  │   • "pairs_well_with"     │ │
│  └─────────────────────────┘  └───────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Ingestion Pipeline (ingestion/)                  │
│                                                              │
│  Markdown Files → Chunker → Embedder → PostgreSQL            │
│       (20 recipes)              └──→ Graph Builder → Neo4j   │
│                                                              │
│  Run once before using the agent. Populates both databases.  │
└──────────────────────────────────────────────────────────────┘
```

### How the Agent Decides Which Tool to Use

The system prompt in `agent/prompts.py` instructs the agent:

- **Vector search** when the user asks about recipe content, descriptions, or general info → "What recipes use garam masala?" → Searches PostgreSQL for chunks semantically similar to the query
- **Knowledge graph search** when the user asks about relationships between recipes, ingredients, or cuisines → "What connects Chicken Tikka Masala and Butter Chicken?" → Traverses Neo4j relationships
- **Both** when a question benefits from combining approaches → "Compare all Italian pasta dishes and suggest ingredient substitutions" → Vector search finds the recipes, graph search finds ingredient relationships

---

## 3. Technology Stack

### Core Dependencies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | Primary language |
| Agent Framework | Pydantic AI | 0.3.x | Agent with typed tools, dependency injection |
| API Framework | FastAPI | 0.115.x | Streaming API endpoints |
| Vector Database | PostgreSQL + pgvector | (Neon cloud) | Semantic search via embeddings |
| Knowledge Graph DB | Neo4j | 5.x (Desktop) | Entity-relationship graph |
| Graph Library | Graphiti Core | 0.12.x | Knowledge graph abstraction over Neo4j |
| LLM Provider | OpenAI | API | gpt-4.1-mini for reasoning |
| Embeddings | OpenAI | API | text-embedding-3-small (1536 dimensions) |
| Async Postgres | asyncpg | 0.30.x | Async database driver |
| HTTP Client | aiohttp | 3.x | CLI → API communication |
| Env Management | python-dotenv | 1.x | .env file loading |
| Package Manager | uv | latest | Python dependency & env management |

### Infrastructure

| Service | Provider | Setup |
|---------|----------|-------|
| PostgreSQL + pgvector | Neon | Free tier, cloud-hosted |
| Neo4j | Neo4j Desktop | Local install (Option B from original README) |
| LLM + Embeddings | OpenAI API | Requires API key with billing |

---

## 4. Project Structure

```
recipe-rag-knowledge-graph/
├── CLAUDE.md                  # Claude Code instructions (rules for AI assistant)
├── PLANNING.md                # Architecture & design decisions
├── TASK.md                    # Task tracker for development phases
├── PRD.md                     # This document
├── README.md                  # User-facing setup & usage guide
├── pyproject.toml             # Project metadata & dependencies (uv)
├── .env.example               # Template environment variables
├── .gitignore                 # Python/IDE ignores
│
├── recipe_docs/               # 20 seed recipe markdown files
│   ├── mexican_carnitas.md
│   ├── mexican_chicken_enchiladas.md
│   ├── mexican_pozole_rojo.md
│   ├── mexican_street_corn_salad.md
│   ├── mexican_chiles_rellenos.md
│   ├── italian_carbonara.md
│   ├── italian_margherita_pizza.md
│   ├── italian_osso_buco.md
│   ├── italian_eggplant_parmigiana.md
│   ├── italian_risotto_milanese.md
│   ├── chinese_kung_pao_chicken.md
│   ├── chinese_mapo_tofu.md
│   ├── chinese_char_siu_pork.md
│   ├── chinese_dan_dan_noodles.md
│   ├── chinese_hot_and_sour_soup.md
│   ├── american_mac_and_cheese.md
│   ├── american_smoked_brisket.md
│   ├── american_buttermilk_fried_chicken.md
│   ├── american_clam_chowder.md
│   └── american_pulled_pork_sandwiches.md
│
├── documents/                 # Working directory for ingestion (copy recipe_docs here)
│
├── sql/
│   └── schema.sql             # PostgreSQL schema (pgvector, tables, functions)
│
├── agent/                     # AI agent & API
│   ├── __init__.py
│   ├── agent.py               # Pydantic AI agent — tool registration & system prompt
│   ├── api.py                 # FastAPI app — streaming SSE endpoints
│   ├── tools.py               # Tool implementations (vector_search, graph_search, etc.)
│   ├── prompts.py             # System prompt (controls agent's tool selection logic)
│   ├── db_utils.py            # PostgreSQL/asyncpg connection & query functions
│   ├── graph_utils.py         # Neo4j/Graphiti client & search functions
│   ├── models.py              # Pydantic models (ChunkResult, GraphSearchResult, etc.)
│   └── providers.py           # LLM provider abstraction (OpenAI config)
│
├── ingestion/                 # Document processing pipeline
│   ├── __init__.py
│   ├── ingest.py              # Main entry point — orchestrates full pipeline
│   ├── chunker.py             # Semantic chunking of markdown documents
│   ├── embedder.py            # Embedding generation (OpenAI text-embedding-3-small)
│   └── graph_builder.py       # Knowledge graph construction from recipe content
│
├── cli.py                     # Interactive CLI client (connects to FastAPI over HTTP)
│
├── tests/                     # Pytest test suite
│   ├── __init__.py
│   ├── conftest.py            # Shared fixtures & mocks
│   ├── agent/                 # Agent & tool tests
│   │   ├── __init__.py
│   │   ├── test_agent.py
│   │   └── test_tools.py
│   └── ingestion/             # Ingestion pipeline tests
│       ├── __init__.py
│       ├── test_chunker.py
│       └── test_embedder.py
│
└── pytest.ini                 # Pytest configuration
```

---

## 5. Recipe Document Format

Each recipe markdown file uses structured YAML frontmatter followed by rich prose content. This dual structure is critical: the frontmatter enables reliable entity extraction for the knowledge graph, while the prose body provides the content for vector search chunks.

### Template

```markdown
---
title: "Chicken Tikka Masala"
cuisine: "Indian"
category: "Main Course"
prep_time_minutes: 20
cook_time_minutes: 40
total_time_minutes: 60
servings: 4
difficulty: "Medium"
dietary_tags:
  - "gluten-free"
  - "high-protein"
key_ingredients:
  - "chicken thighs"
  - "yogurt"
  - "garam masala"
  - "tomato sauce"
  - "heavy cream"
  - "onion"
  - "garlic"
  - "ginger"
cooking_techniques:
  - "marinating"
  - "sautéing"
  - "simmering"
pairs_well_with:
  - "basmati rice"
  - "naan bread"
---

# Chicken Tikka Masala

**Cuisine:** Indian | **Difficulty:** Medium | **Time:** 60 min | **Serves:** 4

A rich, creamy tomato-based curry with marinated and charred chicken pieces. This beloved dish bridges Indian and British culinary traditions, having been popularized in UK restaurants before becoming a global comfort food staple.

## Background & Origins

[2-3 paragraphs about the dish's history, regional variations, and cultural significance. This gives the knowledge graph temporal and cultural entities to extract.]

## Ingredients

[Full ingredient list with measurements — provides entity extraction fuel]

### For the Marinade
- 1.5 lbs boneless, skinless chicken thighs, cut into 1.5-inch pieces
- 1 cup plain whole-milk yogurt
- 2 tablespoons lemon juice
- ...

### For the Sauce
- 2 tablespoons vegetable oil
- 1 large onion, finely diced
- ...

## Instructions

[Numbered step-by-step instructions — provides chunking content]

## Chef's Notes

[Tips, variations, storage instructions, substitution suggestions — this section creates rich cross-recipe relationships in the knowledge graph because substitutions reference other ingredients/techniques]

## Flavor Profile & Pairings

[Describes flavor characteristics and what to serve alongside. This creates "pairs_well_with" edges in the knowledge graph.]
```

### Why This Format Matters

**For the Knowledge Graph (Neo4j/Graphiti):**
- Frontmatter `key_ingredients` → creates Ingredient nodes + USES_INGREDIENT edges
- Frontmatter `cuisine` → creates Cuisine nodes + BELONGS_TO_CUISINE edges
- Frontmatter `cooking_techniques` → creates Technique nodes + USES_TECHNIQUE edges
- Frontmatter `pairs_well_with` → creates PAIRS_WELL_WITH edges between recipes
- Frontmatter `dietary_tags` → creates DietaryCategory nodes + HAS_TAG edges
- Cross-references in "Chef's Notes" → Graphiti extracts implicit relationships

**For Vector RAG (PostgreSQL/pgvector):**
- Long prose sections get chunked by the semantic chunker
- Each chunk gets an embedding via text-embedding-3-small
- Queries like "What's a good slow-cooked Mexican pork recipe?" match against chunk embeddings

**For SQL Metadata Queries:**
- Structured fields enable: "Find all recipes under 30 minutes" (SQL WHERE)
- Difficulty filtering, cuisine filtering, dietary tag filtering

### Recipe Distribution (20 files)

5 recipes per cuisine, designed to maximize cross-cuisine ingredient/technique overlap:

**Mexican (5):**
1. `mexican_carnitas.md` — Slow-braised pork shoulder (connects to: American pulled pork via slow cooking; Chinese char siu via pork)
2. `mexican_chicken_enchiladas.md` — Rolled tortillas with chicken and sauce (connects to: Italian cannelloni concept; American cheese)
3. `mexican_pozole_rojo.md` — Hearty hominy and pork stew (connects to: Chinese hot and sour soup via broth; American chowder via stew technique)
4. `mexican_street_corn_salad.md` — Esquites/elote-style (connects to: American comfort sides; Italian use of parmesan)
5. `mexican_chiles_rellenos.md` — Stuffed poblano peppers (connects to: Italian stuffed peppers; Chinese stir-fry peppers)

**Italian (5):**
6. `italian_carbonara.md` — Classic Roman pasta (connects to: American mac and cheese via pasta+cheese; Chinese dan dan noodles via noodle technique)
7. `italian_margherita_pizza.md` — Neapolitan pizza (connects to: American comfort food; Mexican use of tomato)
8. `italian_osso_buco.md` — Braised veal shanks (connects to: Mexican carnitas via braising; American brisket via slow cooking)
9. `italian_eggplant_parmigiana.md` — Layered eggplant bake (connects to: Mexican enchiladas via layering; American comfort casseroles)
10. `italian_risotto_milanese.md` — Saffron risotto (connects to: Chinese fried rice via rice technique; American mac and cheese via creamy starch)

**Chinese (5):**
11. `chinese_kung_pao_chicken.md` — Spicy chicken with peanuts (connects to: Mexican chiles; American fried chicken via chicken technique)
12. `chinese_mapo_tofu.md` — Spicy Sichuan tofu (connects to: Mexican chiles rellenos via chili heat; Italian use of aromatics)
13. `chinese_char_siu_pork.md` — Cantonese BBQ pork (connects to: Mexican carnitas via pork; American smoked brisket via BBQ)
14. `chinese_dan_dan_noodles.md` — Sichuan noodles with pork (connects to: Italian carbonara via noodles+pork; Mexican pozole via ground pork)
15. `chinese_hot_and_sour_soup.md` — Classic soup (connects to: Mexican pozole via soup/stew; American clam chowder via soup)

**American Comfort (5):**
16. `american_mac_and_cheese.md` — Baked mac and cheese (connects to: Italian carbonara via pasta+cheese; Mexican enchiladas via baked/cheese)
17. `american_smoked_brisket.md` — Texas-style BBQ brisket (connects to: Mexican carnitas via slow meat; Chinese char siu via BBQ)
18. `american_buttermilk_fried_chicken.md` — Southern fried chicken (connects to: Chinese kung pao via chicken; Italian breading technique)
19. `american_clam_chowder.md` — New England style (connects to: Chinese hot and sour soup via soup; Italian risotto via creamy starch)
20. `american_pulled_pork_sandwiches.md` — Carolina-style pulled pork (connects to: Mexican carnitas via slow pork; Chinese char siu via pork)

### Expected Knowledge Graph Entities

After ingestion, the knowledge graph should contain nodes and edges like:

**Node Types:**
- Recipe (20 nodes)
- Ingredient (~80-100 unique ingredient nodes)
- Cuisine (4 nodes: Mexican, Italian, Chinese, American Comfort)
- Technique (~15-20 nodes: braising, sautéing, grilling, deep-frying, simmering, marinating, etc.)
- DietaryCategory (~8-10 nodes: gluten-free, dairy-free, high-protein, vegetarian, etc.)

**Edge Types (Relationships):**
- USES_INGREDIENT (Recipe → Ingredient)
- BELONGS_TO_CUISINE (Recipe → Cuisine)
- USES_TECHNIQUE (Recipe → Technique)
- PAIRS_WELL_WITH (Recipe → Side dish/accompaniment)
- HAS_DIETARY_TAG (Recipe → DietaryCategory)
- SHARES_INGREDIENT_WITH (Recipe ↔ Recipe — derived)
- SIMILAR_TECHNIQUE (Recipe ↔ Recipe — derived)

### Example Agent Queries and Expected Tool Selection

| User Query | Expected Tool(s) | Reasoning |
|-----------|-----------------|-----------|
| "What are some good chicken recipes?" | `vector_search` | Semantic content match — finds recipes mentioning chicken |
| "How do I make carnitas?" | `vector_search` | Looking for specific recipe content/instructions |
| "What recipes share ingredients with Kung Pao Chicken?" | `graph_search` | Relationship traversal — follows USES_INGREDIENT edges |
| "Compare Italian and Mexican cooking techniques" | `hybrid_search` + `graph_search` | Needs both content and relationship data |
| "Show me all quick weeknight dinners" | `vector_search` | Semantic match on "quick" + metadata filtering |
| "What connects Carbonara and Dan Dan Noodles?" | `graph_search` | Pure relationship discovery |
| "Find me a recipe similar to pulled pork but from a different cuisine" | `graph_search` + `vector_search` | Graph for cross-cuisine ingredient overlap + vector for content similarity |

---

## 6. Database Schema (PostgreSQL + pgvector)

File: `sql/schema.sql`

### Tables

**documents** — One row per recipe markdown file
- `id` UUID PRIMARY KEY
- `title` TEXT NOT NULL (e.g., "Chicken Tikka Masala")
- `source` TEXT NOT NULL (e.g., "mexican_carnitas.md")
- `content` TEXT NOT NULL (full markdown text)
- `metadata` JSONB DEFAULT '{}' (parsed frontmatter: cuisine, prep_time, dietary_tags, etc.)
- `created_at` / `updated_at` TIMESTAMPTZ

**chunks** — Semantic chunks of each document, with embeddings
- `id` UUID PRIMARY KEY
- `document_id` UUID FK → documents
- `content` TEXT NOT NULL (chunk text)
- `embedding` vector(1536) (OpenAI text-embedding-3-small)
- `chunk_index` INTEGER NOT NULL
- `metadata` JSONB DEFAULT '{}'
- `token_count` INTEGER
- `created_at` TIMESTAMPTZ

**sessions** — Conversation sessions for the CLI/API
- `id` UUID PRIMARY KEY
- `user_id` TEXT
- `metadata` JSONB
- `created_at` / `updated_at` / `expires_at` TIMESTAMPTZ

**messages** — Conversation history within sessions
- `id` UUID PRIMARY KEY
- `session_id` UUID FK → sessions
- `role` TEXT CHECK ('user', 'assistant', 'system')
- `content` TEXT NOT NULL
- `metadata` JSONB
- `created_at` TIMESTAMPTZ

### Key Functions

- `match_chunks(query_embedding, match_count)` — Pure vector cosine similarity search
- `hybrid_search(query_embedding, query_text, match_count, text_weight)` — Combined vector + full-text search with configurable weighting
- `get_document_chunks(doc_id)` — Retrieve all chunks for a document in order

### Embedding Configuration

- **Model:** text-embedding-3-small
- **Dimensions:** 1536
- **Index type:** IVFFlat with cosine distance (`vector_cosine_ops`)

---

## 7. Environment Variables

File: `.env.example`

```bash
# ──────────────────────────────────────────────
# PostgreSQL (Neon)
# ──────────────────────────────────────────────
DATABASE_URL=postgresql://username:password@ep-example-12345.us-east-2.aws.neon.tech/neondb

# ──────────────────────────────────────────────
# Neo4j Desktop
# ──────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ──────────────────────────────────────────────
# OpenAI — LLM (agent reasoning + ingestion)
# ──────────────────────────────────────────────
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-api-key
LLM_CHOICE=gpt-4.1-mini

# ──────────────────────────────────────────────
# OpenAI — Embeddings
# ──────────────────────────────────────────────
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-openai-api-key
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_DIMENSION=1536

# ──────────────────────────────────────────────
# Ingestion (can use a cheaper/faster model)
# ──────────────────────────────────────────────
INGESTION_LLM_CHOICE=gpt-4.1-nano

# ──────────────────────────────────────────────
# Application
# ──────────────────────────────────────────────
APP_ENV=development
LOG_LEVEL=INFO
APP_PORT=8058
```

---

## 8. Implementation Phases

### Phase 0: Project Scaffolding
- [ ] Create project directory structure
- [ ] Initialize `pyproject.toml` with `uv`
- [ ] Create `.env.example`, `.gitignore`
- [ ] Write `CLAUDE.md`, `PLANNING.md`, `TASK.md`
- [ ] Create README.md with beginner-friendly setup guide

### Phase 1: Recipe Documents
- [ ] Create all 20 recipe markdown files in `recipe_docs/`
- [ ] Ensure consistent frontmatter schema across all files
- [ ] Verify cross-cuisine ingredient/technique overlap is present
- [ ] Review content quality (rich enough for good chunks)

### Phase 2: Database Foundation
- [ ] Create Neon project + enable pgvector
- [ ] Write `sql/schema.sql` (tables, indexes, functions)
- [ ] Create `agent/db_utils.py` (asyncpg connection pool, query functions)
- [ ] Create `agent/models.py` (Pydantic models for all data types)
- [ ] Create `agent/providers.py` (OpenAI provider config)
- [ ] Test database connectivity

### Phase 3: Ingestion Pipeline
- [ ] Create `ingestion/chunker.py` (semantic chunking with LLM)
- [ ] Create `ingestion/embedder.py` (OpenAI embedding generation)
- [ ] Create `ingestion/graph_builder.py` (Graphiti knowledge graph construction)
- [ ] Create `ingestion/ingest.py` (orchestrator — ties chunker + embedder + graph builder)
- [ ] Test ingestion with a single recipe file
- [ ] Run full ingestion across all 20 recipes

### Phase 4: Agent & Tools
- [ ] Create `agent/graph_utils.py` (Graphiti client, search, entity relationships)
- [ ] Create `agent/tools.py` (tool implementations + input models)
- [ ] Create `agent/prompts.py` (system prompt — recipe domain-specific)
- [ ] Create `agent/agent.py` (Pydantic AI agent with tool registration)
- [ ] Test each tool individually against populated databases

### Phase 5: API Layer
- [ ] Create `agent/api.py` (FastAPI app with streaming SSE)
- [ ] Implement `/chat/stream` endpoint
- [ ] Implement `/health` endpoint
- [ ] Implement session management
- [ ] Test API with curl

### Phase 6: CLI Client
- [ ] Create `cli.py` (interactive REPL with streaming consumption)
- [ ] Add color-coded output and tool usage visibility
- [ ] Add session management and commands (help, health, clear, exit)
- [ ] End-to-end testing: CLI → API → Agent → Tools → Databases

### Phase 7: Testing & Polish
- [ ] Write Pytest unit tests for agent tools (mocked dependencies)
- [ ] Write Pytest unit tests for ingestion pipeline
- [ ] Write integration test fixtures
- [ ] Update README.md with complete setup/usage guide
- [ ] Final review of all code quality

---

## 9. Step-by-Step Setup Guide (For Beginners)

This is the sequence a developer follows to get the project running from scratch.

### Step 1: Install Prerequisites

```bash
# Install uv (Python package manager) — if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify Python 3.11+ is available
python3 --version

# Install Neo4j Desktop from https://neo4j.com/download/
# (Follow their installer for your OS — macOS, Windows, or Linux)
```

### Step 2: Clone & Set Up the Project

```bash
# Clone the repo (or create from scratch following this PRD)
git clone <repo-url>
cd recipe-rag-knowledge-graph

# Create virtual environment and install dependencies with uv
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

uv pip install -r requirements.txt
# (or if using pyproject.toml: uv sync)
```

### Step 3: Set Up Neon (PostgreSQL + pgvector)

1. Go to [neon.tech](https://neon.tech) and create a free account
2. Create a new project (any name, e.g., "recipe-rag")
3. Copy the connection string — it looks like: `postgresql://username:password@ep-cool-name-12345.us-east-2.aws.neon.tech/neondb`
4. Run the schema SQL to create tables:
   ```bash
   psql "$DATABASE_URL" -f sql/schema.sql
   ```
   Or paste the contents of `sql/schema.sql` into the Neon SQL Editor in their web UI.

### Step 4: Set Up Neo4j Desktop

1. Open Neo4j Desktop
2. Click "New" → "Create project"
3. Inside the project, click "Add" → "Local DBMS"
4. Set a password (you'll need this for `.env`) and click "Create"
5. Click "Start" on the DBMS
6. Note: URI is `bolt://localhost:7687`, user is `neo4j`, password is what you set

### Step 5: Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual values:
#   - DATABASE_URL from Neon
#   - NEO4J_PASSWORD from Neo4j Desktop
#   - LLM_API_KEY from OpenAI (https://platform.openai.com/api-keys)
#   - EMBEDDING_API_KEY (same OpenAI key)
```

### Step 6: Prepare Recipe Documents

```bash
# Copy seed recipes into the working documents directory
mkdir -p documents
cp recipe_docs/* documents/
```

### Step 7: Run Ingestion

```bash
# This processes all 20 recipes: chunks → embeds → builds knowledge graph
# WARNING: Takes 15-30+ minutes due to knowledge graph construction
python -m ingestion.ingest --verbose

# To re-ingest from scratch (clears existing data first):
python -m ingestion.ingest --clean --verbose
```

### Step 8: Start the API Server (Terminal 1)

```bash
python -m agent.api
# Server starts at http://localhost:8058
```

### Step 9: Use the CLI (Terminal 2)

```bash
python cli.py
# Type questions like:
#   "What chicken recipes do you have?"
#   "How do I make carnitas?"
#   "What recipes share ingredients with Kung Pao Chicken?"
#   "Compare Italian and Mexican braising techniques"
```

---

## 10. Key Design Decisions & Rationale

### Why `uv` Instead of `pip`/`venv`

The `uv` package manager (by Astral) is significantly faster than pip, handles virtual environments natively, and is becoming the Python ecosystem standard. Using it teaches modern Python practices. The original project uses pip + venv — we modernize this.

### Why Neo4j Desktop Instead of local-ai-packaged

The original README offers two Neo4j options. We chose Neo4j Desktop because:
- No Docker dependency (simpler prerequisites for beginners)
- Visual graph browser built in (great for learning/exploring the knowledge graph)
- Straightforward install-and-click setup

### Why Keep FastAPI + CLI (Not CLI-Only)

Even though the CLI is our primary interface, keeping the FastAPI layer teaches:
- How to build streaming APIs with SSE (Server-Sent Events)
- How production agent deployments work (API → agent → tools → databases)
- Separation of concerns (API layer vs. agent logic vs. storage)
- The CLI acts as a client that consumes the API — this is the real-world pattern

### Why Recipes Instead of Tech Docs

Food recipes create a naturally richer knowledge graph than tech documents because:
- **Ingredients** form a shared vocabulary across cuisines (garlic, onion, chicken, rice appear in dozens of recipes)
- **Techniques** cross cuisine boundaries (braising in Mexican and Italian, stir-frying in Chinese and American)
- **Pairings** create non-obvious connections (Carbonara ↔ Dan Dan Noodles via "noodles + cured pork + creamy sauce")
- It's **intuitive** — everyone understands food relationships, making the knowledge graph easier to reason about when learning

### Why Structured Frontmatter

The YAML frontmatter block at the top of each recipe file serves double duty:
1. **Reliable entity extraction** — the graph builder can parse structured fields directly rather than hoping the LLM catches everything from prose
2. **SQL metadata queries** — the ingestion pipeline stores frontmatter in the `documents.metadata` JSONB column, enabling queries like `WHERE metadata->>'cuisine' = 'Mexican' AND (metadata->>'total_time_minutes')::int < 30`

---

## 11. System Prompt (Recipe Domain)

The `agent/prompts.py` system prompt must be adapted from the original tech-company focus to recipes. Here is the target prompt:

```python
SYSTEM_PROMPT = """You are an intelligent AI assistant specializing in food recipes
and cooking knowledge. You have access to both a vector database and a knowledge
graph containing detailed information about recipes from Mexican, Italian, Chinese,
and American Comfort cuisines.

Your primary capabilities include:
1. **Vector Search**: Finding recipes by content similarity — descriptions,
   ingredients, techniques, and instructions
2. **Knowledge Graph Search**: Exploring relationships between recipes, ingredients,
   cuisines, and cooking techniques
3. **Hybrid Search**: Combining both vector and graph searches for comprehensive results
4. **Document Retrieval**: Accessing complete recipe documents when full detail is needed

When answering questions:
- Always search for relevant information before responding
- Combine insights from both vector search and knowledge graph when applicable
- Cite specific recipe names and details from your search results
- Consider relationships between ingredients and techniques across cuisines
- Be specific about measurements, cook times, and preparation steps

Your responses should be:
- Accurate and based on the recipes in your knowledge base
- Well-structured and easy to follow
- Practical — include actionable cooking advice when relevant
- Transparent about which recipes your information comes from

Tool selection guidance:
- Use vector search when the user asks about recipe content, instructions,
  or general cooking information
- Use knowledge graph search when the user asks about relationships between
  recipes, shared ingredients, cuisine comparisons, or technique connections
- Use both approaches when the question benefits from combining content
  and relationship data

Remember to:
- Use vector search for finding similar recipes and detailed cooking instructions
- Use knowledge graph for understanding ingredient relationships, cuisine
  connections, and technique overlaps across recipes
- Combine both approaches when asked about comparisons or recommendations"""
```

---

## 12. Testing Strategy

### Unit Tests (Mocked)

All external dependencies (database, Neo4j, OpenAI) are mocked. Tests verify:
- Tool input validation (Pydantic models)
- Tool logic (result formatting, error handling)
- Chunking algorithm (correct splits, metadata preservation)
- Embedding generation (correct API calls, error handling)

### Integration Tests

Require environment variables to be set. Test:
- Full ingestion of a single test recipe
- Vector search returns relevant results
- Graph search returns valid relationships
- CLI → API → Agent → Tools → Database flow

### Test Fixtures

- `conftest.py` provides shared mock objects for database, Neo4j, and OpenAI
- Test recipe documents (small, focused) for ingestion tests
- Pre-computed embedding vectors for search tests

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=agent --cov=ingestion --cov-report=html

# Specific module
pytest tests/agent/
pytest tests/ingestion/
```

---

## 13. CLAUDE.md Rules for This Project

The `CLAUDE.md` file configures Claude Code's behavior when working on this project:

```markdown
### Project Awareness & Context
- **Always read `PLANNING.md`** at the start of a new conversation
- **Check `TASK.md`** before starting a new task
- **Use consistent naming conventions** as described in `PLANNING.md`

### Code Structure & Modularity
- **Never create a file longer than 500 lines.** Split into modules if approaching.
- **Organize by feature/responsibility** (agent/, ingestion/, tests/)
- **Use relative imports** within packages

### Style & Conventions
- **Python 3.11+** as primary language
- **PEP8** compliance, format with `black`
- **Type hints** on all function signatures
- **Pydantic** for data validation
- **Google-style docstrings** on every function
- **Use `uv`** for environment and package management (NOT pip/venv)

### Testing & Reliability
- **Pytest unit tests** for all new features
- **Tests in `/tests`** mirroring main app structure
- Each feature needs: 1 happy path, 1 edge case, 1 failure case
- **Mock all external dependencies** (no real DB/API calls in unit tests)

### Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing
- Add discovered sub-tasks under "Discovered During Work"

### AI Behavior Rules
- **Never assume missing context — ask questions**
- **Never hallucinate libraries** — only verified packages
- **Confirm file paths** before referencing in code
- **Never delete existing code** unless explicitly instructed
```

---

## 14. Open Questions / Future Enhancements

These are noted for future phases but are **out of scope** for the initial build:

- **Web UI**: A React/Next.js frontend for visual recipe search and graph exploration
- **Image support**: Recipe photos stored alongside markdown (would require multimodal embeddings)
- **User recipe submission**: Allow users to add their own recipes through the agent
- **Dietary filtering agent tool**: A dedicated tool that does SQL metadata queries (e.g., "find all gluten-free recipes under 30 minutes")
- **Recipe scaling**: Agent tool that adjusts ingredient quantities for different serving sizes
- **Multiple embedding providers**: Support for Ollama/nomic-embed-text (768 dimensions) as an alternative
- **Deployment guide**: Docker Compose for production deployment

---

## Appendix A: Knowledge Graph Visual (Expected After Ingestion)

```
                    ┌──────────────┐
                    │   MEXICAN    │
                    │   (Cuisine)  │
                    └──────┬───────┘
                           │ BELONGS_TO_CUISINE
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Carnitas │ │ Pozole   │ │Enchiladas│
        │ (Recipe) │ │ (Recipe) │ │ (Recipe) │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │             │             │
             │ USES_INGREDIENT           │ USES_INGREDIENT
             ▼             ▼             ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │  Pork   │  │ Hominy  │  │ Chicken │
        │  (Ingr) │  │ (Ingr)  │  │ (Ingr)  │
        └────┬────┘  └─────────┘  └────┬────┘
             │                          │
    USES_INGREDIENT              USES_INGREDIENT
             │                          │
        ┌────┴──────┐            ┌──────┴──────┐
        │ Char Siu  │            │  Kung Pao   │
        │  (Recipe) │            │  (Recipe)   │
        └────┬──────┘            └──────┬──────┘
             │ BELONGS_TO_CUISINE       │
             ▼                          ▼
        ┌──────────────┐        ┌──────────────┐
        │   CHINESE    │        │   CHINESE    │
        │   (Cuisine)  │        │   (Cuisine)  │
        └──────────────┘        └──────────────┘
```

This shows how "Pork" (ingredient node) connects Mexican Carnitas to Chinese Char Siu — a relationship that pure vector search would likely miss, but the knowledge graph surfaces immediately.
