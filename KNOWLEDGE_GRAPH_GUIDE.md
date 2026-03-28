# Knowledge Graph + Vector RAG: A Comprehensive Guide

A deep-dive into how this project combines vector search and knowledge graphs to build an intelligent recipe assistant. This guide is written for developers who are new to either or both technologies.

---

## Table of Contents

1. [Introduction: Why Knowledge Graphs?](#1-introduction-why-knowledge-graphs)
2. [Knowledge Graph Fundamentals](#2-knowledge-graph-fundamentals)
3. [Vector Database Fundamentals](#3-vector-database-fundamentals)
4. [Comparing Vector Search vs Knowledge Graph](#4-comparing-vector-search-vs-knowledge-graph)
5. [How It Works in This Project](#5-how-it-works-in-this-project)
6. [The Ingestion Pipeline — Building the Graph](#6-the-ingestion-pipeline--building-the-graph)
7. [Query Patterns: Vector vs Graph vs Hybrid](#7-query-patterns-vector-vs-graph-vs-hybrid)
8. [Cross-Cuisine Connections — The Power of Graphs](#8-cross-cuisine-connections--the-power-of-graphs)
9. [Neo4j & Graphiti Deep Dive](#9-neo4j--graphiti-deep-dive)
10. [The Agent: Choosing the Right Tool](#10-the-agent-choosing-the-right-tool)
11. [Hands-On Exercises](#11-hands-on-exercises)
12. [Key Takeaways](#12-key-takeaways)

---

## 1. Introduction: Why Knowledge Graphs?

### The Limitation of Keyword and Vector-Only Search

Traditional recipe search works by matching keywords — search "chicken soup" and you get documents containing those words. Vector search (also called semantic search) improved on this by understanding *meaning*: searching "warm comforting broth" would match chicken soup even without exact keywords.

But both approaches share a fundamental blind spot: **they treat documents as isolated islands**. Neither can answer questions that require understanding *relationships between things*:

- "What Mexican and Chinese recipes share the same protein?"
- "Which recipes use the same braising technique as Osso Buco?"
- "If I have pork shoulder, what can I make across all four cuisines?"
- "What pairs well with something that pairs well with Carnitas?"

These questions require **reasoning about connections** — and that's exactly what knowledge graphs enable.

### What Questions KGs Can Answer That Vectors Cannot

| Question Type | Vector Search | Knowledge Graph |
|---------------|:------------:|:---------------:|
| "Find recipes similar to this description" | Yes | No |
| "What ingredients are in Carbonara?" | Partial (might find chunks mentioning them) | Yes (direct lookup) |
| "What recipes share ingredients with Carnitas?" | No | Yes |
| "Show me the path from Mac & Cheese to Dan Dan Noodles" | No | Yes |
| "What cuisines use braising?" | Partial | Yes |
| "What goes well with something that goes well with brisket?" | No | Yes (2-hop traversal) |

### Real-World Examples

Knowledge graphs power some of the most sophisticated information systems:

- **Google Knowledge Graph**: When you search "Tom Hanks," Google shows his movies, co-stars, awards, and family — all from a graph of relationships, not keyword matching.
- **Netflix Recommendations**: Beyond "users who watched X also watched Y," Netflix models relationships between genres, actors, directors, and themes.
- **This Project**: We model recipes, ingredients, cuisines, and techniques as interconnected entities, enabling questions that span across the entire recipe collection.

---

## 2. Knowledge Graph Fundamentals

### Nodes (Entities) and Edges (Relationships)

A knowledge graph has two primary building blocks:

- **Nodes** (also called entities or vertices): Things that exist. In our domain: recipes, ingredients, cuisines, techniques, equipment.
- **Edges** (also called relationships): Connections between nodes. In our domain: USES_INGREDIENT, BELONGS_TO_CUISINE, USES_TECHNIQUE, PAIRS_WELL_WITH.

```
[Carnitas] --USES_INGREDIENT--> [pork shoulder]
[Carnitas] --BELONGS_TO_CUISINE--> [Mexican]
[Carnitas] --USES_TECHNIQUE--> [braising]
[Carnitas] --PAIRS_WELL_WITH--> [corn tortillas]
```

### Properties on Nodes and Edges

Both nodes and edges can carry **properties** — key-value metadata:

```
Node: Carnitas
  type: Recipe
  servings: 8
  prep_time: 20 minutes
  difficulty: Medium

Edge: Carnitas --USES_INGREDIENT--> pork shoulder
  amount: "3 lbs"
  role: "primary protein"
```

### Directed vs Undirected Relationships

Relationships have **direction**. "Carnitas USES_INGREDIENT pork shoulder" is different from "pork shoulder USES_INGREDIENT Carnitas" (which would make no sense). Direction matters because:

- `Carnitas --BELONGS_TO_CUISINE--> Mexican` means Carnitas is *in* Mexican cuisine
- `Mexican --BELONGS_TO_CUISINE--> Carnitas` would incorrectly imply Mexican cuisine belongs to Carnitas

Most graph databases (including Neo4j) store directed edges, but you can traverse them in either direction during queries.

### Graph Traversal Concepts

The power of graphs comes from **traversal** — following edges from node to node:

**1-hop query**: What ingredients does Carnitas use?
```
[Carnitas] --USES_INGREDIENT--> [pork shoulder]
[Carnitas] --USES_INGREDIENT--> [lard]
[Carnitas] --USES_INGREDIENT--> [orange juice]
...
```

**2-hop query**: What other recipes use the same ingredients as Carnitas?
```
[Carnitas] --USES_INGREDIENT--> [pork shoulder] <--USES_INGREDIENT-- [Char Siu]
[Carnitas] --USES_INGREDIENT--> [pork shoulder] <--USES_INGREDIENT-- [Pulled Pork]
[Carnitas] --USES_INGREDIENT--> [garlic] <--USES_INGREDIENT-- [Kung Pao Chicken]
```

**Path query**: How are Mac & Cheese and Dan Dan Noodles connected?
```
[Mac & Cheese] --USES_TECHNIQUE--> [sauce building] <--USES_TECHNIQUE-- [Dan Dan Noodles]
```

Both are noodle/pasta dishes that build a rich sauce from scratch — a relationship impossible to discover through keyword or vector search alone.

### Comparison: Relational DB Tables vs Graph

In a relational database, you'd model this with join tables:

```sql
-- Relational approach: need JOIN tables
recipes (id, name, cuisine_id)
ingredients (id, name)
recipe_ingredients (recipe_id, ingredient_id, amount)
cuisines (id, name)
techniques (id, name)
recipe_techniques (recipe_id, technique_id)
```

Finding "recipes that share 3+ ingredients with Carnitas" requires multi-level JOINs that get slow and complex. In a graph, the same query is a natural traversal:

```cypher
// Graph approach: natural traversal
MATCH (carnitas:Recipe {name: "Carnitas"})-[:USES_INGREDIENT]->(ing)<-[:USES_INGREDIENT]-(other:Recipe)
WITH other, COUNT(ing) as shared
WHERE shared >= 3
RETURN other.name, shared
```

---

## 3. Vector Database Fundamentals

### Embeddings and Semantic Similarity

An **embedding** is a list of numbers (a vector) that captures the *meaning* of a piece of text. Two texts with similar meaning will have vectors that are close together in mathematical space.

For example, the OpenAI `text-embedding-3-small` model (used in this project) converts text into a 1536-dimensional vector:

```python
"slow braised pork in its own fat"  → [0.023, -0.156, 0.089, ..., 0.034]  # 1536 numbers
"meat cooked low and slow in lard"  → [0.021, -0.148, 0.091, ..., 0.037]  # very similar!
"crispy deep-fried tofu cubes"      → [-0.132, 0.045, -0.067, ..., 0.112] # very different
```

### How Cosine Distance Works

To measure how similar two embeddings are, we use **cosine similarity**: the cosine of the angle between two vectors.

- **1.0** = identical meaning (vectors point the same direction)
- **0.0** = unrelated (vectors are perpendicular)
- **-1.0** = opposite meaning (rare in practice)

The formula is:

```
similarity(A, B) = (A · B) / (|A| × |B|)
```

PostgreSQL with pgvector uses the `<=>` operator for cosine *distance* (1 - similarity), so smaller distances mean more similar content:

```sql
-- From our schema (sql/schema.sql)
SELECT content, 1 - (embedding <=> query_embedding) AS similarity
FROM chunks
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

### Strengths of Vector Search

- **Fuzzy matching**: "comfort food with cheese" matches Mac & Cheese even without those exact words
- **Multilingual potential**: Embeddings can capture meaning across languages
- **No schema required**: Any text can be embedded — no need to define entity types in advance
- **Handles nuance**: "spicy numbing Sichuan flavors" finds Mapo Tofu and Kung Pao Chicken

### Weaknesses of Vector Search

- **No explicit relationships**: Cannot answer "what recipes share ingredients?" — only "what text is similar?"
- **Context window**: Each chunk is searched independently; relationships spanning chunks are invisible
- **No reasoning about connections**: Cannot traverse from recipe A to recipe B through shared attributes
- **Similarity ≠ relationship**: Two recipe chunks may be semantically similar without being meaningfully related

---

## 4. Comparing Vector Search vs Knowledge Graph

### Side-by-Side Comparison

| Dimension | Vector Search (pgvector) | Knowledge Graph (Neo4j) |
|-----------|--------------------------|------------------------|
| **Data model** | Chunks of text + embedding vectors | Nodes (entities) + edges (relationships) |
| **Query style** | "Find text similar to this meaning" | "Traverse connections between entities" |
| **Best for** | Semantic similarity, fuzzy matching, natural language | Relationship queries, multi-hop reasoning, structured facts |
| **Weakness** | No explicit relationships | No fuzzy/semantic understanding |
| **Storage** | PostgreSQL + pgvector extension | Neo4j graph database |
| **Index type** | HNSW (Hierarchical Navigable Small World) | Native graph indexes |
| **Query language** | SQL with vector operators | Cypher |
| **Schema needs** | Minimal (just text + vector) | Entity types and relationship types |
| **Scales to** | Millions of embeddings | Billions of nodes/edges |

### When to Use Which (With Recipe Examples)

**Use vector search when:**
- User describes what they want in natural language: *"I want a slow-cooked meat dish with warm spices"*
- Query is fuzzy or exploratory: *"something like a hearty Italian stew"*
- User wants full recipe content: *"How do I make Carbonara?"*

**Use knowledge graph when:**
- Query involves relationships: *"What ingredients does Carnitas share with Char Siu?"*
- Query involves filtering by structured attributes: *"All Mexican recipes"*
- Query involves multi-hop reasoning: *"Recipes using techniques from both Italian and Chinese cooking"*

**Use both (hybrid) when:**
- Query combines natural language with relationship needs: *"Italian recipes similar to Mac and Cheese"*
- Comprehensive answers require both content and context: *"Tell me everything about pork shoulder recipes"*

---

## 5. How It Works in This Project

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   User Query                             │
│         "What Mexican recipes use braising?"             │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Layer                          │
│                   (agent/api.py)                          │
│            Receives query, manages sessions               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  Pydantic AI Agent                        │
│                 (agent/agent.py)                          │
│                                                          │
│  The agent reads the query and decides which tool(s)     │
│  to use. For this query, it would choose graph_search    │
│  because the user is asking about cuisine + technique    │
│  relationships.                                          │
└────────────┬─────────────────────────┬──────────────────┘
             │                         │
             ▼                         ▼
┌────────────────────────┐ ┌──────────────────────────────┐
│   PostgreSQL + pgvector │ │   Neo4j + Graphiti            │
│   (agent/db_utils.py)   │ │   (agent/graph_utils.py)      │
│                         │ │                                │
│ - vector_search()       │ │ - search_knowledge_graph()     │
│ - hybrid_search()       │ │ - get_recipes_by_ingredient()  │
│ - get_document()        │ │ - get_recipes_by_cuisine()     │
│ - list_documents()      │ │ - get_similar_recipes()        │
│                         │ │ - get_entity_relationships()   │
└────────────────────────┘ └──────────────────────────────┘
```

### The Recipe Data Model

**Entity types** in the knowledge graph:

| Entity Type | Examples | Count in System |
|-------------|----------|:---------------:|
| Recipe | Carnitas, Carbonara, Kung Pao Chicken | 20 |
| Ingredient | pork shoulder, garlic, soy sauce | ~100+ unique |
| Cuisine | Mexican, Italian, Chinese, American Comfort | 4 |
| Technique | braising, stir-frying, baking | ~40+ unique |
| Equipment | wok, Dutch oven, grill | varies |

**Relationship types**:

| Relationship | Meaning | Example |
|-------------|---------|---------|
| USES_INGREDIENT | Recipe uses this ingredient | Carnitas → pork shoulder |
| BELONGS_TO_CUISINE | Recipe is part of this cuisine | Carbonara → Italian |
| USES_TECHNIQUE | Recipe employs this cooking technique | Osso Buco → braising |
| REQUIRES_EQUIPMENT | Recipe needs this equipment | Kung Pao Chicken → wok |
| PAIRS_WELL_WITH | Recipe goes well with this food/drink | Carbonara → white wine |

### Visual Example: Carnitas and Its Connections

```
                        [Mexican] ◄──BELONGS_TO_CUISINE── [Pozole Rojo]
                            ▲                                   │
                            │                            USES_INGREDIENT
                    BELONGS_TO_CUISINE                          │
                            │                                   ▼
[corn tortillas] ◄──PAIRS_WELL_WITH── [Carnitas] ──USES_INGREDIENT──► [pork shoulder]
                                          │                               ▲
                                    USES_TECHNIQUE              USES_INGREDIENT
                                          │                               │
                                          ▼                          [Char Siu]
                                      [braising]                          │
                                          ▲                       BELONGS_TO_CUISINE
                                    USES_TECHNIQUE                        │
                                          │                               ▼
                                     [Osso Buco] ──BELONGS_TO_CUISINE──► [Italian]
```

This small subgraph already reveals:
- **Ingredient bridge**: Carnitas and Char Siu both use pork shoulder (Mexican ↔ Chinese)
- **Technique bridge**: Carnitas and Osso Buco both use braising (Mexican ↔ Italian)
- **Cuisine clusters**: Carnitas and Pozole Rojo cluster under Mexican

---

## 6. The Ingestion Pipeline — Building the Graph

The ingestion pipeline takes raw recipe markdown files and loads them into both the vector database and the knowledge graph. This is orchestrated by `ingestion/ingest.py`.

### Step-by-Step Walkthrough

```
recipe_docs/mexican_carnitas.md
        │
        ▼
┌──────────────────────────────────┐
│  1. Read file & parse frontmatter │  (chunker.py)
│     YAML metadata → dict          │
│     Markdown body → string        │
└──────────────┬───────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌──────────────┐ ┌─────────────────────┐
│ 2a. Chunk    │ │ 2b. Extract entities │  (graph_builder.py)
│  document    │ │  from frontmatter    │
│ (chunker.py) │ │  key_ingredients → USES_INGREDIENT
│              │ │  cooking_techniques → USES_TECHNIQUE
│              │ │  cuisine → BELONGS_TO_CUISINE
│              │ │  pairs_well_with → PAIRS_WELL_WITH
└──────┬───────┘ └──────────┬──────────┘
       │                    │
       ▼                    ▼
┌──────────────┐ ┌─────────────────────┐
│ 3a. Generate │ │ 3b. Add episode to  │
│  embeddings  │ │  Graphiti (Neo4j)   │
│ (embedder.py)│ │  (graph_builder.py) │
└──────┬───────┘ └──────────┬──────────┘
       │                    │
       ▼                    ▼
┌──────────────┐ ┌─────────────────────┐
│ 4a. Store    │ │ 4b. Graphiti runs   │
│  chunks +    │ │  LLM entity         │
│  embeddings  │ │  extraction &       │
│  in Postgres │ │  creates nodes/     │
│              │ │  edges in Neo4j     │
└──────────────┘ └─────────────────────┘
```

### YAML Frontmatter → Entity Extraction

Each recipe file starts with YAML frontmatter containing structured metadata:

```yaml
---
title: "Carnitas (Mexican Slow-Braised Pulled Pork)"
cuisine: "Mexican"
servings: 8
difficulty: "Medium"
key_ingredients:
  - "pork shoulder"
  - "lard"
  - "orange juice"
  - "garlic"
cooking_techniques:
  - "braising"
  - "slow cooking"
  - "crisping"
pairs_well_with:
  - "corn tortillas"
  - "salsa verde"
---
```

The `GraphBuilder.extract_entities()` method in `ingestion/graph_builder.py` reads each frontmatter field and creates entity/relationship pairs:

```python
# From ingestion/graph_builder.py:extract_entities()

# Cuisine → BELONGS_TO_CUISINE relationship
cuisine = metadata.get("cuisine")
if cuisine:
    entities.append(RecipeEntity(name=cuisine, entity_type="Cuisine"))
    relations.append(RecipeRelation(
        source=recipe_name,
        relation_type="BELONGS_TO_CUISINE",
        target=cuisine,
    ))

# Ingredients → USES_INGREDIENT relationships
ingredients = metadata.get("key_ingredients", metadata.get("ingredients", []))
for ingredient in ingredients:
    entities.append(RecipeEntity(name=ingredient, entity_type="Ingredient"))
    relations.append(RecipeRelation(
        source=recipe_name,
        relation_type="USES_INGREDIENT",
        target=ingredient,
    ))
```

### Graphiti Episodes: How Recipes Become Graph Nodes

After extracting structured entities, the full recipe content is sent to [Graphiti](https://github.com/getzep/graphiti) as an **episode**. Graphiti uses an LLM to:

1. Identify additional entities and relationships beyond what the frontmatter captures
2. Deduplicate entities (e.g., "garlic cloves" and "garlic" are the same ingredient)
3. Create temporal edges with `valid_at` timestamps

```python
# From ingestion/graph_builder.py:add_recipe_to_graph()
episode = await client.add_episode(
    name=recipe_name,
    episode_body=episode_content,
    source=EpisodeType.text,
    source_description=f"Recipe: {title} ({cuisine} cuisine)",
    reference_time=datetime.now(timezone.utc),
)
```

### How Chunking + Embedding Works (For the Vector DB)

Simultaneously, the recipe content is chunked and embedded for vector search:

1. **Chunking** (`ingestion/chunker.py`): Splits the markdown by sections (## headers), then by paragraphs within sections. Target chunk size is ~800 characters with ~150 character overlap.

2. **Embedding** (`ingestion/embedder.py`): Each chunk is sent to OpenAI's `text-embedding-3-small` model, which returns a 1536-dimensional vector.

3. **Storage**: Chunks and their embeddings are stored in PostgreSQL using the `pgvector` extension.

A typical recipe produces 5-10 chunks. Across 20 recipes, the vector database holds ~100-200 chunks with embeddings.

---

## 7. Query Patterns: Vector vs Graph vs Hybrid

### Vector Query Example

**User asks**: *"slow cooked meat dishes with rich flavors"*

This is a semantic/fuzzy query — no specific entity names, just a description of what they want. The agent uses `vector_search`.

```python
# How it works internally (agent/tools.py:vector_search_tool)
embedding = await generate_embedding("slow cooked meat dishes with rich flavors")
results = await db_utils.vector_search(embedding, limit=5)
```

The SQL executed (from `sql/schema.sql`):

```sql
-- match_chunks() function
SELECT c.id AS chunk_id, c.document_id, d.title AS document_title,
       c.content, 1 - (c.embedding <=> query_embedding) AS similarity
FROM chunks c
JOIN documents d ON c.document_id = d.id
ORDER BY c.embedding <=> query_embedding
LIMIT 5;
```

**Results might include**: Carnitas (braised pork), Osso Buco (braised veal), Smoked Brisket (slow-smoked beef) — ranked by how semantically similar their content is to the query.

### Graph Query Example

**User asks**: *"What recipes share ingredients with Carnitas?"*

This is a relationship traversal query. The agent uses `graph_search` or the specialized `get_similar_recipes` tool.

```python
# How it works internally (agent/graph_utils.py:get_similar_recipes)
query = """
MATCH (recipe:Entity)-[r1]->(shared)<-[r2]-(similar:Entity)
WHERE recipe.name =~ '(?i).*Carnitas.*'
  AND recipe <> similar
WITH similar, COUNT(DISTINCT shared) as shared_count,
     COLLECT(DISTINCT shared.name) as shared_items
ORDER BY shared_count DESC
LIMIT 5
RETURN similar.name as recipe, shared_count, shared_items
"""
```

**Results might include**:
- Char Siu: shares pork shoulder, garlic (2 ingredients)
- Pulled Pork: shares pork shoulder, cumin (2 ingredients)
- Pozole Rojo: shares garlic, onion, cumin, oregano (4 ingredients)

### Hybrid Query Example

**User asks**: *"Italian recipes similar to Mac and Cheese"*

This query needs both: semantic understanding of "similar to Mac and Cheese" (vector search) and filtering by cuisine "Italian" (graph search). The agent might use `hybrid_search` or run both tools.

```python
# The hybrid_search SQL function combines vector + full-text
SELECT chunk_id, document_title, content,
       (0.7 * vector_score + 0.3 * text_score) AS combined_score
FROM hybrid_search(query_embedding, 'Italian recipes cheese pasta', 10, 0.3);
```

**Results might include**: Carbonara (pasta + cheese + fat emulsion), Eggplant Parmigiana (cheese-heavy Italian comfort), Risotto (creamy Italian starch dish).

### Actual Cypher Queries from graph_utils.py

Finding recipes by ingredient (`agent/graph_utils.py:get_recipes_by_ingredient`):

```cypher
MATCH (recipe:Entity)-[r:USES_INGREDIENT|CONTAINS]->(ingredient:Entity)
WHERE ingredient.name =~ '(?i).*pork shoulder.*'
RETURN DISTINCT recipe.name as recipe, ingredient.name as ingredient
LIMIT 10
```

Finding recipes by cuisine (`agent/graph_utils.py:get_recipes_by_cuisine`):

```cypher
MATCH (recipe:Entity)-[r:BELONGS_TO_CUISINE|CUISINE]->(cuisine:Entity)
WHERE cuisine.name =~ '(?i).*Mexican.*'
RETURN DISTINCT recipe.name as recipe, cuisine.name as cuisine
LIMIT 10
```

---

## 8. Cross-Cuisine Connections — The Power of Graphs

The 20 recipes in this project were deliberately chosen to create a rich web of cross-cuisine connections. These connections are invisible to vector search but immediately visible in the knowledge graph.

### Ingredient Bridges

**Pork shoulder** connects three cuisines:

```
[Carnitas] ──── pork shoulder ──── [Char Siu]
  Mexican                           Chinese
     └──────── pork shoulder ──── [Pulled Pork]
                                   American
```

**Garlic** is the great unifier — used in recipes from every cuisine:
- Mexican: Carnitas, Pozole Rojo, Enchiladas
- Italian: Carbonara, Osso Buco, Eggplant Parmigiana
- Chinese: Kung Pao Chicken, Mapo Tofu, Char Siu, Dan Dan Noodles
- American: Fried Chicken, Pulled Pork

**Cumin** bridges Mexican and American:
- Mexican: Carnitas, Pozole Rojo
- American: Pulled Pork (in the dry rub)

### Technique Bridges

**Braising** connects Mexican and Italian:
```
[Carnitas] ──── braising ──── [Osso Buco]
  Mexican                       Italian
```

**Slow cooking** spans three cuisines:
```
[Carnitas] ──── slow cooking ──── [Osso Buco]
  Mexican                           Italian
     └──────── slow cooking ──── [Pulled Pork]
                                   American
```

**Boiling** connects Italian, Chinese, and American:
- Italian: Carbonara (pasta)
- Chinese: Dan Dan Noodles
- American: Mac and Cheese (macaroni)

**Sauce building** connects Chinese and American:
```
[Dan Dan Noodles] ──── sauce building ──── [Mac and Cheese]
     Chinese                                 American
```

### Structural Bridges: The Noodle/Pasta Web

One of the most interesting cross-cuisine connections:

```
[Carbonara] ───── "pasta + rendered fat + savory sauce" ───── [Dan Dan Noodles]
   Italian                                                       Chinese
      │                                                             │
      └──── "noodles/pasta + cheese/cream sauce" ──── [Mac & Cheese]
                                                        American
```

All three are fundamentally "starch + rich sauce" dishes. In the knowledge graph, they're connected through:
- Shared technique: **boiling** (cooking the noodles/pasta)
- Shared technique: **tossing** (coating with sauce)
- Shared concept: starch as a vehicle for a rich sauce

### The Pairing Web

The `pairs_well_with` relationships create another layer of connections:

```
[Mac & Cheese] --PAIRS_WELL_WITH--> [pulled pork]
[Mac & Cheese] --PAIRS_WELL_WITH--> [fried chicken]
[Mac & Cheese] --PAIRS_WELL_WITH--> [smoked brisket]
[Pulled Pork]  --PAIRS_WELL_WITH--> [coleslaw]
[Pulled Pork]  --PAIRS_WELL_WITH--> [mac and cheese]  ← circular!
```

This creates a natural "meal planning" graph: if you're making Pulled Pork, the graph tells you it pairs well with Mac & Cheese and coleslaw — a classic BBQ plate.

---

## 9. Neo4j & Graphiti Deep Dive

### What Is Neo4j?

[Neo4j](https://neo4j.com/) is a native graph database. Unlike relational databases that store data in tables with rows and columns, Neo4j stores data as nodes and relationships directly. This makes relationship traversal extremely fast — O(1) per hop rather than O(n) for a JOIN.

**Cypher** is Neo4j's query language, designed to be visually intuitive:

```cypher
-- "Find recipes that use pork shoulder"
MATCH (recipe)-[:USES_INGREDIENT]->(ing {name: "pork shoulder"})
RETURN recipe.name
```

The pattern `(recipe)-[:USES_INGREDIENT]->(ing)` visually represents a node, an edge, and another node — you can almost see the graph in the query.

### What Graphiti Adds on Top of Neo4j

[Graphiti](https://github.com/getzep/graphiti) (by Zep) is a library that adds intelligence on top of raw Neo4j:

1. **LLM-Powered Entity Extraction**: Feed Graphiti a text blob and it uses an LLM to identify entities and relationships automatically, rather than requiring manual extraction.

2. **Episode-Based Ingestion**: Data is added as "episodes" — chunks of information that Graphiti processes into graph nodes and edges.

3. **Temporal Edges**: Every relationship has `valid_at` and `invalid_at` timestamps, supporting questions like "what was the recipe for X before it was updated?"

4. **Semantic Search Over Graph**: Graphiti adds embedding-based search over the graph itself, combining the strengths of both approaches.

5. **Entity Resolution**: Graphiti deduplicates entities — "garlic cloves," "fresh garlic," and "garlic" get merged into a single node.

### Episodes, Entities, and Relationships in Graphiti's Model

```
Episode (a piece of source content):
  ├── name: "mexican_carnitas"
  ├── body: "Recipe: Carnitas. Cuisine: Mexican. Ingredients: pork shoulder, lard..."
  ├── source: EpisodeType.text
  └── reference_time: 2025-01-15T10:30:00Z

     Graphiti LLM processing extracts:
     ├── Entity: Carnitas (type: Recipe)
     ├── Entity: pork shoulder (type: Ingredient)
     ├── Entity: Mexican (type: Cuisine)
     ├── Relationship: Carnitas --USES_INGREDIENT--> pork shoulder
     └── Relationship: Carnitas --BELONGS_TO_CUISINE--> Mexican
```

### How Temporal Edges Work

Every edge in Graphiti has temporal metadata:

```python
edge = {
    "source": "Carnitas",
    "target": "pork shoulder",
    "relation": "USES_INGREDIENT",
    "valid_at": "2025-01-15T10:30:00Z",   # when this fact was recorded
    "invalid_at": None,                     # still valid (not superseded)
}
```

If a recipe is updated (e.g., a new version replaces lard with vegetable oil), the old edge gets an `invalid_at` timestamp and a new edge is created. This provides a full audit trail.

### How Graphiti Is Initialized in This Project

```python
# From agent/graph_utils.py:GraphitiClient.initialize()
self._graphiti = Graphiti(
    neo4j_uri,          # bolt://localhost:7687
    neo4j_user,         # neo4j
    neo4j_password,
    llm_client=llm_client,      # OpenAI GPT-4.1-mini for entity extraction
    embedder=embedder,           # text-embedding-3-small for graph embeddings
)
await self._graphiti.build_indices_and_constraints()
```

---

## 10. The Agent: Choosing the Right Tool

### How the Pydantic AI Agent Decides

The agent is configured in `agent/agent.py` with a system prompt (from `agent/prompts.py`) that tells the LLM which tools are available and when to use each one.

The key decision framework from the system prompt:

```
Use vector_search when:
  → User asks about recipe content, instructions, descriptions
  → "How do I make Carbonara?"

Use graph_search when:
  → User asks about relationships between entities
  → "What recipes share ingredients with Carnitas?"

Use hybrid_search when:
  → User needs comprehensive results
  → "Italian recipes similar to Mac and Cheese"
```

### Tool Selection Examples with Reasoning

**Query**: *"What's a good recipe with lots of cheese?"*

Agent reasoning: This is a semantic/descriptive query. The user wants recipes where cheese is prominent. → `vector_search("recipes with lots of cheese")`

**Query**: *"What Mexican recipes are in the system?"*

Agent reasoning: This is a structured query about cuisine membership. → `graph_search` via `get_recipes_by_cuisine("Mexican")`

**Query**: *"If I have pork shoulder, what can I make?"*

Agent reasoning: This is an ingredient-based relationship query. → `graph_search` via `get_recipes_by_ingredient("pork shoulder")`

**Query**: *"Tell me everything about slow cooking techniques across cuisines"*

Agent reasoning: This needs both semantic content (descriptions of techniques) and relationship data (which cuisines use it). → Use both `vector_search("slow cooking techniques")` AND `graph_search("slow cooking")` for a comprehensive answer.

### The Tool Registration Code

```python
# From agent/agent.py (simplified)
from pydantic_ai import Agent

rag_agent = Agent(
    model=get_llm_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=[
        vector_search_tool,
        graph_search_tool,
        hybrid_search_tool,
        get_document_tool,
        list_documents_tool,
        entity_relationship_tool,
        find_recipes_by_ingredient_tool,
        find_recipes_by_cuisine_tool,
        find_similar_recipes_tool,
    ],
)
```

Each tool function has type-annotated inputs (Pydantic models in `agent/tools.py`) that the LLM uses to understand what parameters to provide.

---

## 11. Hands-On Exercises

### Exercise 1: Query the Neo4j Browser Directly

1. Open Neo4j Desktop and start your database
2. Open the Neo4j Browser (usually at http://localhost:7474)
3. Run these Cypher queries:

```cypher
-- See all entity types
MATCH (n) RETURN DISTINCT labels(n), count(n)

-- See all relationship types
MATCH ()-[r]->() RETURN DISTINCT type(r), count(r)

-- Find all recipes
MATCH (r:Entity) WHERE r.name =~ '(?i).*(carnitas|carbonara|kung pao|mac and cheese).*'
RETURN r.name

-- Visualize Carnitas and all its connections
MATCH (carnitas:Entity)-[r]-(connected)
WHERE carnitas.name =~ '(?i).*carnitas.*'
RETURN carnitas, r, connected
```

The last query will display an interactive graph visualization in the Neo4j Browser — you can drag nodes around and explore the connections visually.

### Exercise 2: Add a New Recipe and Trace It Through Ingestion

1. Create a new recipe file `recipe_docs/mexican_guacamole.md`:

```markdown
---
title: "Classic Guacamole"
cuisine: "Mexican"
category: "Side Dish"
prep_time_minutes: 10
cook_time_minutes: 0
total_time_minutes: 10
servings: 4
difficulty: "Easy"
key_ingredients:
  - "avocado"
  - "lime juice"
  - "cilantro"
  - "onion"
  - "jalapeño"
  - "salt"
cooking_techniques:
  - "mashing"
  - "mixing"
pairs_well_with:
  - "corn tortillas"
  - "carnitas"
---

# Classic Guacamole

A simple, fresh guacamole recipe...
```

2. Run the ingestion pipeline for just this file:

```bash
uv run python -m ingestion.ingest --dir recipe_docs --verbose --clean
```

3. Verify in Neo4j Browser:

```cypher
-- Find the new guacamole recipe and its connections
MATCH (g:Entity)-[r]-(connected)
WHERE g.name =~ '(?i).*guacamole.*'
RETURN g, r, connected
```

4. Notice how guacamole automatically connects to Carnitas through shared ingredients (onion, jalapeño, lime juice) and through the `pairs_well_with` relationship.

### Exercise 3: Write a Custom Cypher Query

Write a Cypher query that answers: **"What is the shortest path between Mac and Cheese and Mapo Tofu in the knowledge graph?"**

Hint:

```cypher
MATCH path = shortestPath(
  (mac:Entity)-[*]-(mapo:Entity)
)
WHERE mac.name =~ '(?i).*mac.*cheese.*'
  AND mapo.name =~ '(?i).*mapo.*tofu.*'
RETURN path
```

What connections did it find? The path likely goes through a shared ingredient (like garlic) or a shared technique.

### Exercise 4: Compare Vector vs Graph Results for the Same Question

Start the API server and ask the same question using different search modes:

```bash
# Start the server
uv run uvicorn agent.api:app --host 0.0.0.0 --port 8058

# Vector search
curl -X POST http://localhost:8058/search/vector \
  -H "Content-Type: application/json" \
  -d '{"query": "recipes with pork shoulder", "limit": 5}'

# Graph search
curl -X POST http://localhost:8058/search/graph \
  -H "Content-Type: application/json" \
  -d '{"query": "recipes with pork shoulder", "limit": 5}'
```

Compare the results:
- **Vector search** returns chunks of recipe text that mention pork shoulder or similar concepts
- **Graph search** returns relationship facts connecting recipes to the pork shoulder ingredient

The vector results include rich context (full paragraphs about cooking techniques) while graph results give structured facts (which exact recipes use pork shoulder).

---

## 12. Key Takeaways

### When Knowledge Graphs Add Value Over Vector-Only RAG

1. **Relationship-heavy domains**: When users care about connections between entities (recipes ↔ ingredients, products ↔ categories, people ↔ organizations).

2. **Multi-hop reasoning**: When answers require traversing multiple levels of connections ("recipes that pair well with things that pair well with X").

3. **Structured filtering + semantic search**: When users need both ("Italian recipes similar to...").

4. **Explanation and provenance**: Graphs can explain *why* two things are related (shared 3 ingredients, same technique), not just *that* they're similar.

5. **Growing interconnected datasets**: As you add more recipes, the graph gets exponentially more valuable because each new recipe creates connections to existing ones.

### Cost/Complexity Tradeoffs

| Factor | Vector-Only RAG | Vector + Knowledge Graph |
|--------|:---------------:|:------------------------:|
| Infrastructure | PostgreSQL only | PostgreSQL + Neo4j |
| Ingestion complexity | Chunk + embed | Chunk + embed + entity extraction |
| API cost per ingestion | Embedding only | Embedding + LLM entity extraction |
| Query complexity | Single SQL query | SQL + Cypher |
| Maintenance | One database | Two databases to keep in sync |
| Development time | Lower | Higher |
| Query power | Semantic only | Semantic + relational |

**Rule of thumb**: If users only ask "find me something like X," vector-only is sufficient. If users ask "how is X related to Y" or "what connects X and Z," you need a knowledge graph.

### Scaling Considerations

- **Vector search scales**: pgvector with HNSW indexes handles millions of embeddings. Add more recipes and search stays fast.

- **Knowledge graph scales differently**: Neo4j handles billions of nodes. But Graphiti's LLM-based entity extraction is the bottleneck — each recipe requires LLM calls during ingestion. For 20 recipes this is fine; for 20,000 you'd want batch processing and caching.

- **Hybrid queries** are as fast as the slower component. In practice, both vector and graph queries return in <100ms for this dataset size.

- **Keep data in sync**: When you add a recipe, it must go into both PostgreSQL (chunks + embeddings) and Neo4j (entities + relationships). The ingestion pipeline (`ingestion/ingest.py`) handles this, but if one fails, you can end up with partial data. The `--clean` flag helps by deleting and re-inserting.

### Where to Go From Here

1. **Add more relationship types**: dietary restrictions (SUITABLE_FOR → "gluten-free"), seasonal availability (BEST_IN → "summer"), regional variations (VARIANT_OF → "Texas BBQ").

2. **Add user preferences**: Track which recipes a user has cooked, liked, or bookmarked as graph relationships.

3. **Add ingredient substitutions**: Model SUBSTITUTES_FOR relationships to answer "I don't have guanciale, what can I use instead?"

4. **Explore graph algorithms**: Neo4j supports PageRank (find the most "central" ingredient), community detection (find cuisine sub-clusters), and similarity scoring.

---

## Appendix: File Reference

| File | Purpose |
|------|---------|
| `agent/db_utils.py` | PostgreSQL operations: vector search, document CRUD, chunk storage |
| `agent/graph_utils.py` | Neo4j/Graphiti operations: graph search, entity queries, Cypher |
| `agent/tools.py` | Tool definitions that the AI agent can invoke |
| `agent/agent.py` | Pydantic AI agent configuration and tool registration |
| `agent/prompts.py` | System prompt with tool selection guidance |
| `agent/api.py` | FastAPI endpoints (chat, search, health) |
| `ingestion/ingest.py` | Main ingestion orchestrator |
| `ingestion/chunker.py` | Text chunking with frontmatter parsing |
| `ingestion/embedder.py` | OpenAI embedding generation |
| `ingestion/graph_builder.py` | Entity extraction and Graphiti episode creation |
| `sql/schema.sql` | PostgreSQL schema (tables, indexes, search functions) |
| `recipe_docs/*.md` | 20 recipe markdown files with YAML frontmatter |

---

*This guide accompanies the Recipe RAG Knowledge Graph project. For setup instructions, see README.md. For current development status, see TASK.md.*
