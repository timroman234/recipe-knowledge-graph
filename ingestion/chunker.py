"""Semantic text chunking for recipe documents."""

import os
import re
from dataclasses import dataclass
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    max_chunk_size: int = int(os.getenv("MAX_CHUNK_SIZE", "1500"))


@dataclass
class ChunkResult:
    """Result of chunking a document."""

    content: str
    chunk_index: int
    metadata: dict[str, Any]


class Chunker:
    """Semantic text chunker for recipe documents."""

    def __init__(self, config: ChunkConfig | None = None):
        """Initialize the chunker.

        Args:
            config: Optional chunking configuration.
        """
        self.config = config or ChunkConfig()

    def parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from document content.

        Args:
            content: Document content with optional frontmatter.

        Returns:
            Tuple of (metadata dict, content without frontmatter).
        """
        # Check for YAML frontmatter (between --- markers)
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            try:
                metadata = yaml.safe_load(match.group(1)) or {}
                body = content[match.end() :]
                return metadata, body
            except yaml.YAMLError:
                return {}, content

        return {}, content

    def _split_into_sections(self, content: str) -> list[tuple[str, str]]:
        """Split content into sections based on markdown headers.

        Args:
            content: Document content.

        Returns:
            List of (section_title, section_content) tuples.
        """
        # Pattern for markdown headers (## Header)
        header_pattern = r"^(#{1,3})\s+(.+)$"
        lines = content.split("\n")

        sections: list[tuple[str, str]] = []
        current_title = "Introduction"
        current_content: list[str] = []

        for line in lines:
            match = re.match(header_pattern, line)
            if match:
                # Save previous section if it has content
                if current_content:
                    sections.append(
                        (current_title, "\n".join(current_content).strip())
                    )
                current_title = match.group(2)
                current_content = []
            else:
                current_content.append(line)

        # Don't forget the last section
        if current_content:
            sections.append((current_title, "\n".join(current_content).strip()))

        return sections

    def _split_section_into_chunks(
        self,
        section_title: str,
        section_content: str,
    ) -> list[str]:
        """Split a section into smaller chunks.

        Args:
            section_title: Title of the section.
            section_content: Content of the section.

        Returns:
            List of chunk strings.
        """
        if not section_content:
            return []

        # If section is small enough, return as single chunk
        full_content = f"## {section_title}\n\n{section_content}"
        if len(full_content) <= self.config.max_chunk_size:
            return [full_content]

        # Split by paragraphs first
        paragraphs = re.split(r"\n\n+", section_content)

        chunks: list[str] = []
        current_chunk: list[str] = [f"## {section_title}"]
        current_length = len(current_chunk[0])

        for para in paragraphs:
            para_length = len(para)

            # If adding this paragraph exceeds chunk size
            if current_length + para_length + 2 > self.config.chunk_size:
                # Save current chunk if it has content beyond the header
                if len(current_chunk) > 1:
                    chunks.append("\n\n".join(current_chunk))

                # Start new chunk with overlap from previous
                if chunks and self.config.chunk_overlap > 0:
                    # Include section header and part of previous content
                    current_chunk = [f"## {section_title} (continued)"]
                else:
                    current_chunk = [f"## {section_title}"]
                current_length = len(current_chunk[0])

            current_chunk.append(para)
            current_length += para_length + 2  # +2 for \n\n

        # Don't forget the last chunk
        if len(current_chunk) > 1:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def chunk_document(
        self,
        content: str,
        document_name: str = "",
    ) -> list[ChunkResult]:
        """Chunk a document into smaller pieces.

        Args:
            content: Full document content.
            document_name: Name of the document for metadata.

        Returns:
            List of ChunkResult objects.
        """
        # Parse frontmatter
        metadata, body = self.parse_frontmatter(content)

        # Split into sections
        sections = self._split_into_sections(body)

        # Chunk each section
        chunks: list[ChunkResult] = []
        chunk_index = 0

        for section_title, section_content in sections:
            section_chunks = self._split_section_into_chunks(
                section_title, section_content
            )

            for chunk_content in section_chunks:
                chunks.append(
                    ChunkResult(
                        content=chunk_content,
                        chunk_index=chunk_index,
                        metadata={
                            "document_name": document_name,
                            "section": section_title,
                            **metadata,  # Include frontmatter metadata
                        },
                    )
                )
                chunk_index += 1

        return chunks


def chunk_document(
    content: str,
    document_name: str = "",
    config: ChunkConfig | None = None,
) -> list[ChunkResult]:
    """Convenience function to chunk a document.

    Args:
        content: Document content.
        document_name: Name of the document.
        config: Optional chunking configuration.

    Returns:
        List of ChunkResult objects.
    """
    chunker = Chunker(config)
    return chunker.chunk_document(content, document_name)
