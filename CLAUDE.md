# CLAUDE.md

## Project Awareness & Context

- **Always read `PLANNING.md`** at the start of a new conversation to understand the project architecture, goals, and current state.
- **Check `TASK.md`** before starting work to see current tasks, their status, and any discovered issues.
- **Reference `PRD.md`** for detailed product requirements and acceptance criteria.
- Use consistent naming, structure, and patterns as outlined below.

## Code Structure & Modularity

- **Never create a file longer than 500 lines.** If a file approaches this limit, split it into logical modules.
- **Organize imports** in groups: standard library, third-party, local modules (separated by blank lines).
- **Use absolute imports** within packages (e.g., `from agent.models import ...`).
- **Each module should have a single responsibility.** Split utility functions into dedicated modules.

## Style & Conventions

### Python

- **Python 3.11+** features encouraged (type hints, `match` statements, `|` for union types).
- Follow **PEP 8** with **100-character line limit**.
- Use **type hints** for all function signatures and class attributes.
- Use **docstrings** for public functions and classes (Google style).
- Use **f-strings** for string formatting.
- Prefer **async/await** for I/O operations.

### Naming

- **snake_case** for functions, variables, modules.
- **PascalCase** for classes.
- **UPPER_SNAKE_CASE** for constants.
- Prefix private attributes/methods with single underscore `_`.

### Error Handling

- Use specific exception types, not bare `except:`.
- Log errors with context before re-raising or handling.
- Return structured error responses from API endpoints.

## Testing & Reliability

- **Write tests** for all new functionality.
- **Unit tests** should be isolated with mocked dependencies.
- **Integration tests** require database connections (mark with `@pytest.mark.integration`).
- **Run tests** before committing: `pytest tests/`.
- Test file location mirrors source: `agent/tools.py` → `tests/agent/test_tools.py`.

## Task Completion

- **Update `TASK.md`** when starting, completing, or discovering tasks.
- Mark tasks with status: `[ ]` pending, `[~]` in progress, `[X]` complete.
- **Document discovered issues** in the "Discovered During Work" section.
- Keep task descriptions actionable and specific.

## AI Behavior Rules

- **Ask clarifying questions** when requirements are ambiguous.
- **Propose changes** before making significant architectural modifications.
- **Don't assume** - verify file existence and current implementations before making changes.
- **Provide context** in commit messages and PR descriptions.
- **Keep responses focused** on the specific task at hand.

## Project-Specific Guidelines

### Recipe Domain

- Recipe entities: Recipe, Ingredient, Cuisine, Technique, Equipment.
- Cuisines covered: Mexican, Italian, Chinese, American Comfort.
- Recipe frontmatter contains structured metadata (title, cuisine, servings, prep_time, etc.).

### Database Operations

- Use `asyncpg` for PostgreSQL operations.
- Use connection pools for database access.
- Vectors use `pgvector` extension with 1536 dimensions (OpenAI text-embedding-3-small).

### Knowledge Graph

- Use `graphiti-core` with Neo4j for knowledge graph operations.
- Entities and relationships extracted from recipe frontmatter.
- Graph enables recipe relationship queries (shared ingredients, cuisine connections).

### API Design

- FastAPI with async endpoints.
- SSE streaming for chat responses.
- Health endpoint for monitoring.
- Structured Pydantic models for requests/responses.
