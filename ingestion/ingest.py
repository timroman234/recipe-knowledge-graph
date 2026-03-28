"""Main ingestion pipeline orchestrator."""

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agent import db_utils
from agent.models import IngestionResult
from ingestion.chunker import ChunkConfig, Chunker
from ingestion.embedder import Embedder
from ingestion.graph_builder import GraphBuilder

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class IngestConfig:
    """Configuration for the ingestion pipeline."""

    recipe_docs_dir: Path = Path("recipe_docs")
    verbose: bool = False
    clean: bool = False
    skip_graph: bool = False


class IngestionPipeline:
    """Orchestrates the recipe ingestion pipeline."""

    def __init__(self, config: IngestConfig):
        """Initialize the pipeline.

        Args:
            config: Pipeline configuration.
        """
        self.config = config
        self.chunker = Chunker(ChunkConfig())
        self.embedder = Embedder()
        self.graph_builder = GraphBuilder()

    async def process_single_recipe(
        self,
        file_path: Path,
    ) -> IngestionResult:
        """Process a single recipe file.

        Args:
            file_path: Path to the recipe markdown file.

        Returns:
            IngestionResult with processing details.
        """
        recipe_name = file_path.stem
        logger.info(f"Processing recipe: {recipe_name}")

        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Parse frontmatter
            metadata, body = self.chunker.parse_frontmatter(content)

            # Check if document already exists
            existing_doc = await db_utils.get_document_by_title(recipe_name)
            if existing_doc:
                if not self.config.clean:
                    logger.info(f"Recipe '{recipe_name}' already exists, skipping")
                    return IngestionResult(
                        document_id=existing_doc["id"],
                        document_name=recipe_name,
                        chunks_created=0,
                        graph_entities_created=0,
                        success=True,
                        error="Already exists (skipped)",
                    )
                # Delete existing document (cascades to chunks)
                await db_utils.delete_document(existing_doc["id"])
                logger.info(f"Deleted existing recipe '{recipe_name}'")

            # Create document
            doc = await db_utils.create_document(
                title=recipe_name,
                source=str(file_path),
                content=content,
                metadata=metadata,
            )
            logger.debug(f"Created document: {doc['id']}")

            # Chunk the document
            chunks = self.chunker.chunk_document(content, recipe_name)
            logger.debug(f"Created {len(chunks)} chunks")

            # Generate embeddings
            chunk_texts = [c.content for c in chunks]
            embeddings = await self.embedder.embed_batch(
                chunk_texts,
                show_progress=self.config.verbose,
            )
            logger.debug(f"Generated {len(embeddings)} embeddings")

            # Store chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings):
                await db_utils.create_chunk(
                    document_id=doc["id"],
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    embedding=embedding,
                    metadata=chunk.metadata,
                )

            # Build knowledge graph
            graph_entities = 0
            if not self.config.skip_graph:
                try:
                    graph_result = await self.graph_builder.build_recipe_graph(
                        metadata=metadata,
                        recipe_name=recipe_name,
                        content=content,
                    )
                    graph_entities = graph_result.get("entities_created", 0)
                except Exception as e:
                    logger.warning(f"Failed to build graph for '{recipe_name}': {e}")

            return IngestionResult(
                document_id=doc["id"],
                document_name=recipe_name,
                chunks_created=len(chunks),
                graph_entities_created=graph_entities,
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to process recipe '{recipe_name}': {e}")
            return IngestionResult(
                document_id=None,  # type: ignore
                document_name=recipe_name,
                chunks_created=0,
                graph_entities_created=0,
                success=False,
                error=str(e),
            )

    async def run(self) -> list[IngestionResult]:
        """Run the full ingestion pipeline.

        Returns:
            List of IngestionResult for each processed file.
        """
        # Find all markdown files in recipe_docs
        recipe_files = list(self.config.recipe_docs_dir.glob("*.md"))

        if not recipe_files:
            logger.warning(f"No markdown files found in {self.config.recipe_docs_dir}")
            return []

        logger.info(f"Found {len(recipe_files)} recipe files to process")

        results: list[IngestionResult] = []
        for file_path in recipe_files:
            result = await self.process_single_recipe(file_path)
            results.append(result)

            if self.config.verbose:
                status = "OK" if result.success else f"FAILED: {result.error}"
                logger.info(
                    f"  {result.document_name}: {result.chunks_created} chunks, "
                    f"{result.graph_entities_created} graph entities - {status}"
                )

        # Summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_chunks = sum(r.chunks_created for r in results)
        total_entities = sum(r.graph_entities_created for r in results)

        logger.info(
            f"\nIngestion complete: {successful} successful, {failed} failed\n"
            f"  Total chunks: {total_chunks}\n"
            f"  Total graph entities: {total_entities}"
        )

        return results

    async def close(self) -> None:
        """Clean up resources."""
        await self.graph_builder.close()
        await db_utils.close_db_pool()


async def run_ingestion(
    recipe_docs_dir: str | Path = "recipe_docs",
    verbose: bool = False,
    clean: bool = False,
    skip_graph: bool = False,
) -> list[IngestionResult]:
    """Run the ingestion pipeline.

    Args:
        recipe_docs_dir: Directory containing recipe markdown files.
        verbose: Whether to show detailed progress.
        clean: Whether to delete existing documents before re-ingesting.
        skip_graph: Whether to skip knowledge graph construction.

    Returns:
        List of IngestionResult for each processed file.
    """
    config = IngestConfig(
        recipe_docs_dir=Path(recipe_docs_dir),
        verbose=verbose,
        clean=clean,
        skip_graph=skip_graph,
    )

    await db_utils.initialize_database()

    pipeline = IngestionPipeline(config)
    try:
        return await pipeline.run()
    finally:
        await pipeline.close()


def main() -> None:
    """CLI entry point for ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest recipe documents into the RAG system"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="recipe_docs",
        help="Directory containing recipe markdown files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing documents before re-ingesting",
    )
    parser.add_argument(
        "--skip-graph",
        action="store_true",
        help="Skip knowledge graph construction",
    )

    args = parser.parse_args()

    asyncio.run(
        run_ingestion(
            recipe_docs_dir=args.dir,
            verbose=args.verbose,
            clean=args.clean,
            skip_graph=args.skip_graph,
        )
    )


if __name__ == "__main__":
    main()
