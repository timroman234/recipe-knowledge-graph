# TASK.md

## Current Status

**Active Phase**: Phase 9 - Ingestion Fix & Documentation
**Completed**: Phase 0-6 (Scaffolding through CLI Client), Phase 8 (Frontend), Phase 9 (Ingestion Fix)

## Task Tracker

### Phase 0: Project Scaffolding
- [X] Create pyproject.toml (uv configuration)
- [X] Create .env.example
- [X] Create .gitignore
- [X] Create pytest.ini
- [X] Create CLAUDE.md
- [X] Create PLANNING.md
- [X] Create TASK.md
- [X] Create README.md
- [X] Create sql/schema.sql
- [X] Create agent/ package (9 files)
- [X] Create ingestion/ package (5 files)
- [X] Create cli.py
- [X] Create tests/ (7 files)
- [X] Create documents/ directory with .gitkeep
- [X] Verify scaffolding with `uv sync` and imports

### Phase 1: Recipe Documents
- [X] Create 5 Mexican recipes (Tacos al Pastor, Enchiladas Verdes, Pozole Rojo, Chiles Rellenos, Mole Poblano)
- [X] Create 5 Italian recipes (Spaghetti Carbonara, Margherita Pizza, Risotto Milanese, Ossobuco, Tiramisu)
- [X] Create 5 Chinese recipes (Kung Pao Chicken, Mapo Tofu, Xiaolongbao, Peking Duck, Hot Pot)
- [X] Create 5 American Comfort recipes (Mac and Cheese, Fried Chicken, BBQ Ribs, Meatloaf, Grilled Cheese)

### Phase 2: Database Foundation
- [X] Set up Neon PostgreSQL database
- [X] Run schema.sql to create tables and functions
- [X] Set up Neo4j Desktop and create database
- [X] Verify database connections
- [X] Test pgvector extension

### Phase 3: Ingestion Pipeline
- [X] Implement chunker.py with YAML frontmatter parsing
- [X] Implement embedder.py with OpenAI integration
- [X] Implement graph_builder.py with Graphiti integration
- [X] Implement ingest.py orchestrator
- [X] Run ingestion on all 20 recipes
- [X] Verify data in PostgreSQL and Neo4j

### Phase 4: Agent & Tools (Rewritten to match reference)
- [X] Rewrite sql/schema.sql with title+source columns
- [X] Create sql/migrate.sql for existing data migration
- [X] Rewrite agent/models.py with reference models (ChunkResult, GraphSearchResult, ToolCall, etc.)
- [X] Rewrite agent/providers.py with get_llm_model(), get_embedding_client(), etc.
- [X] Rewrite agent/db_utils.py with DatabasePool class, no threshold searches
- [X] Rewrite agent/graph_utils.py with GraphitiClient class + recipe Cypher queries
- [X] Rewrite agent/tools.py with input models and tool functions
- [X] Rewrite agent/agent.py with module-level rag_agent and RunContext

### Phase 5: API Layer (Rewritten to match reference)
- [X] Rewrite agent/api.py with agent.iter() streaming
- [X] Add search endpoints (/search/vector, /search/graph, /search/hybrid)
- [X] Add /documents endpoint (replaces /recipes)
- [X] Add /sessions/{session_id} endpoint
- [X] Add GZipMiddleware
- [X] Health check returns boolean fields

### Phase 6: CLI Client (Updated)
- [X] Update cli.py SSE parsing for new streaming format
- [X] Fix _format_tools_used to read tool_name key
- [X] Update _list_recipes to use /documents endpoint

### Phase 8: Streamlit Frontend
- [X] Create frontend/ directory structure
- [X] Create frontend/config.py (FrontendConfig, env loading)
- [X] Create frontend/styles.py (IBM Carbon-inspired CSS)
- [X] Create frontend/api_client.py (httpx SSE streaming client)
- [X] Create frontend/components.py (tool cards, health indicator, empty state)
- [X] Create frontend/app.py (main Streamlit app with streaming)
- [X] Create frontend/.streamlit/config.toml (theme configuration)
- [X] Create frontend/requirements.txt (streamlit, httpx, python-dotenv)

### Phase 7: Testing & Polish
- [X] Update tests/conftest.py for new models
- [X] Update tests/agent/test_tools.py for new tool signatures
- [X] Update tests/agent/test_agent.py for new agent pattern
- [ ] Run migration: psql $DATABASE_URL -f sql/migrate.sql
- [ ] Verify import: python -c "from agent.api import app; print('OK')"
- [ ] Start server and test health endpoint
- [ ] Test CLI streaming and tool display
- [ ] Verify no duplicate search results
- [ ] Run pytest tests/

### Phase 9: Ingestion Pipeline Fix & Documentation
- [X] Add 5 ingestion CRUD functions to agent/db_utils.py (get_document_by_title, delete_document, create_document, create_chunk, close_db_pool)
- [X] Add get_graphiti_client() to agent/graph_utils.py
- [X] Fix ingest.py: get_document_by_name → get_document_by_title, .id → ["id"] dict access, name= → title= + source= params
- [X] Fix ingest.py: add initialize_database() call in run_ingestion()
- [X] Fix graph_builder.py: ingredients → key_ingredients, techniques → cooking_techniques (with fallbacks)
- [X] Fix graph_builder.py: add pairs_well_with extraction for PAIRS_WELL_WITH relationships
- [X] Fix graph_builder.py: update _format_recipe_for_graph to use correct frontmatter keys
- [X] Create KNOWLEDGE_GRAPH_GUIDE.md comprehensive training document
- [ ] Verify imports: python -c "from ingestion.ingest import run_ingestion; print('OK')"
- [ ] Run full re-ingestion: uv run python -m ingestion.ingest --dir recipe_docs --verbose --clean
- [ ] Verify API health after ingestion
- [ ] Run pytest tests/

---

## Discovered During Work

- Schema migration needed: `name` -> `title` + `source` columns in documents table
- Sessions table needs `user_id` and `expires_at` columns
- Chunks table needs `token_count` column
- SQL functions rewritten to remove `match_threshold` parameter
- `match_chunks()` and `hybrid_search()` now use `chunk_id` alias and `document_title`/`document_source`
- Agent streaming switched from `run_stream()` to `agent.iter()` for proper tool call extraction
- HealthStatus changed from string fields to boolean fields
- Phase 4 agent rewrite broke 7 ingestion references (db_utils returned dicts not models, function names changed, missing CRUD functions)
- Recipe YAML frontmatter uses `key_ingredients` and `cooking_techniques`, not `ingredients` and `techniques`
- Recipe YAML frontmatter includes `pairs_well_with` field not previously extracted by graph_builder
- Ingestion pipeline was missing `initialize_database()` call before using db_utils functions

---

## Notes

- Using uv instead of pip for dependency management
- Using Neo4j Desktop (Option B) instead of cloud Neo4j
- Recipe documents already exist in recipe_docs/ (20 files)
- documents/ directory is for ingestion working files
- Ingestion modules (chunker, embedder, graph_builder, ingest) were fixed in Phase 9 to match Phase 4 agent rewrite
- KNOWLEDGE_GRAPH_GUIDE.md provides comprehensive training on vector DB + knowledge graph concepts
