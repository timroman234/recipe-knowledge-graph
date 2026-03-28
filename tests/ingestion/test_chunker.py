"""Tests for the document chunker."""

import pytest

from ingestion.chunker import Chunker, ChunkConfig, ChunkResult, chunk_document


@pytest.mark.unit
class TestChunkerParseFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_parse_frontmatter_extracts_metadata(self, sample_recipe_content):
        """Test that frontmatter is correctly parsed."""
        chunker = Chunker()
        metadata, body = chunker.parse_frontmatter(sample_recipe_content)

        assert metadata["title"] == "Test Tacos"
        assert metadata["cuisine"] == "Mexican"
        assert metadata["servings"] == 4

    def test_parse_frontmatter_removes_from_body(self, sample_recipe_content):
        """Test that frontmatter is removed from body."""
        chunker = Chunker()
        metadata, body = chunker.parse_frontmatter(sample_recipe_content)

        assert "---" not in body.strip()[:10]
        assert "# Test Tacos" in body

    def test_parse_frontmatter_handles_no_frontmatter(self):
        """Test handling content without frontmatter."""
        content = "# Just a Title\n\nSome content here."
        chunker = Chunker()
        metadata, body = chunker.parse_frontmatter(content)

        assert metadata == {}
        assert body == content

    def test_parse_frontmatter_handles_invalid_yaml(self):
        """Test handling invalid YAML in frontmatter."""
        content = "---\ninvalid: yaml: content:\n---\n\n# Title"
        chunker = Chunker()
        metadata, body = chunker.parse_frontmatter(content)

        # Should return empty metadata on parse error
        assert metadata == {}


@pytest.mark.unit
class TestChunkerSplitting:
    """Tests for document splitting."""

    def test_chunk_document_creates_chunks(self, sample_recipe_content):
        """Test that chunk_document creates multiple chunks."""
        chunker = Chunker()
        chunks = chunker.chunk_document(sample_recipe_content, "test_recipe")

        assert len(chunks) > 0
        assert all(isinstance(c, ChunkResult) for c in chunks)

    def test_chunk_preserves_frontmatter_in_metadata(self, sample_recipe_content):
        """Test that frontmatter is preserved in chunk metadata."""
        chunker = Chunker()
        chunks = chunker.chunk_document(sample_recipe_content, "test_recipe")

        # All chunks should have the recipe metadata
        for chunk in chunks:
            assert chunk.metadata.get("cuisine") == "Mexican"
            assert chunk.metadata.get("document_name") == "test_recipe"

    def test_chunk_indices_are_sequential(self, sample_recipe_content):
        """Test that chunk indices are sequential starting from 0."""
        chunker = Chunker()
        chunks = chunker.chunk_document(sample_recipe_content, "test_recipe")

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_respects_max_size(self):
        """Test that chunks respect maximum size."""
        # Create content that would be large
        long_content = "# Title\n\n" + "This is a test paragraph. " * 100

        config = ChunkConfig(chunk_size=200, max_chunk_size=500)
        chunker = Chunker(config)
        chunks = chunker.chunk_document(long_content, "test")

        for chunk in chunks:
            # Allow some flexibility for section headers
            assert len(chunk.content) < config.max_chunk_size + 100


@pytest.mark.unit
class TestChunkerSections:
    """Tests for section-based splitting."""

    def test_splits_by_headers(self):
        """Test that content is split by markdown headers."""
        content = """# Main Title

Introduction text.

## Section One

Section one content.

## Section Two

Section two content.
"""
        chunker = Chunker()
        chunks = chunker.chunk_document(content, "test")

        # Should have separate chunks for different sections
        section_names = [c.metadata.get("section") for c in chunks]
        assert "Introduction" in section_names or "Main Title" in section_names
        assert "Section One" in section_names
        assert "Section Two" in section_names


@pytest.mark.unit
class TestChunkDocumentFunction:
    """Tests for the convenience function."""

    def test_chunk_document_function(self, sample_recipe_content):
        """Test the module-level chunk_document function."""
        chunks = chunk_document(sample_recipe_content, "test")

        assert len(chunks) > 0
        assert all(isinstance(c, ChunkResult) for c in chunks)

    def test_chunk_document_with_custom_config(self, sample_recipe_content):
        """Test chunk_document with custom configuration."""
        config = ChunkConfig(chunk_size=100, chunk_overlap=20)
        chunks = chunk_document(sample_recipe_content, "test", config=config)

        assert len(chunks) > 0
