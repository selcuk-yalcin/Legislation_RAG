"""
Web Document Chunker
Splits fetched web documents into semantic chunks based on content type.
- Legal Markdown: splits on ### headings (Azure DI output)
- Plain text: splits on paragraph boundaries
Attaches regulation/madde metadata to each chunk.
"""

import re
from typing import List, Dict, Optional


class WebDocumentChunker:
    """
    Splits web-sourced documents into meaningful chunks
    using heading-based (semantic) splitting for legal texts
    and paragraph-based splitting for plain text.
    """

    # Defaults
    MAX_CHUNK_SIZE = 1500
    MIN_CHUNK_SIZE = 100
    OVERLAP_CHARS = 200

    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 100,
        overlap: int = 200,
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        print(
            f" WebDocumentChunker initialized "
            f"(max={max_chunk_size}, min={min_chunk_size}, overlap={overlap})"
        )

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def chunk_document(
        self,
        text: str,
        source_url: str,
        source_title: str,
        content_type: str = "markdown",
    ) -> List[Dict]:
        """
        Split a document into chunks with metadata.

        Args:
            text: Full document text (Markdown or plain).
            source_url: URL where the document was fetched from.
            source_title: Human-readable title.
            content_type: 'markdown' for Azure DI output, 'plain' otherwise.

        Returns:
            List of dicts: {content, metadata{source_url, source_title, ...}}
        """
        if not text or len(text.strip()) < self.min_chunk_size:
            return []

        if content_type == "markdown":
            raw_chunks = self._split_by_headings(text)
        else:
            raw_chunks = self._split_by_paragraphs(text)

        # Attach metadata
        chunks = []
        for idx, chunk_text in enumerate(raw_chunks):
            if len(chunk_text.strip()) < self.min_chunk_size:
                continue

            regulation, madde = self._extract_regulation_info(chunk_text, source_title)

            chunks.append({
                "content": chunk_text.strip(),
                "metadata": {
                    "source_url": source_url,
                    "source_title": source_title,
                    "document_title": regulation or source_title,
                    "madde_number": madde,
                    "chunk_index": idx,
                    "chunk_type": content_type,
                    "origin": "web_search",
                },
            })

        print(f"    Chunked into {len(chunks)} pieces (from {len(text):,} chars)")
        return chunks

    # ──────────────────────────────────────────────
    # Splitting strategies
    # ──────────────────────────────────────────────

    def _split_by_headings(self, text: str) -> List[str]:
        """
        Split Markdown text on ### headings (Azure DI output).
        Each heading starts a new chunk. Oversized chunks are
        further split at paragraph boundaries.
        """
        # Pattern: lines starting with one or more '#'
        heading_pattern = re.compile(r"^(#{1,6}\s.+)$", re.MULTILINE)
        parts = heading_pattern.split(text)

        # Recombine heading with its body
        sections: List[str] = []
        current = ""
        for part in parts:
            if heading_pattern.match(part):
                if current.strip():
                    sections.append(current.strip())
                current = part + "\n"
            else:
                current += part

        if current.strip():
            sections.append(current.strip())

        # Break oversized sections
        final: List[str] = []
        for sec in sections:
            if len(sec) <= self.max_chunk_size:
                final.append(sec)
            else:
                final.extend(self._split_large_section(sec))

        return final

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        Split plain text on double-newline paragraph boundaries.
        Merge small paragraphs; split oversized ones.
        """
        paragraphs = re.split(r"\n\n+", text)
        chunks: List[str] = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) + 2 <= self.max_chunk_size:
                current = f"{current}\n\n{para}" if current else para
            else:
                if current:
                    chunks.append(current)
                if len(para) > self.max_chunk_size:
                    chunks.extend(self._split_large_section(para))
                    current = ""
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks

    def _split_large_section(self, text: str) -> List[str]:
        """
        Break an oversized section into max_chunk_size pieces
        with overlap, splitting at sentence boundaries when possible.
        """
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: List[str] = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= self.max_chunk_size:
                current = f"{current} {sentence}" if current else sentence
            else:
                if current:
                    chunks.append(current)
                    # Overlap: keep tail of previous chunk
                    overlap_text = current[-self.overlap :] if len(current) > self.overlap else ""
                    current = overlap_text + " " + sentence
                else:
                    # Single sentence exceeds max — force split
                    for i in range(0, len(sentence), self.max_chunk_size):
                        chunks.append(sentence[i : i + self.max_chunk_size])
                    current = ""

        if current.strip():
            chunks.append(current.strip())

        return chunks

    # ──────────────────────────────────────────────
    # Metadata extraction helpers
    # ──────────────────────────────────────────────

    def _extract_regulation_info(
        self, chunk_text: str, fallback_title: str
    ) -> tuple:
        """
        Try to extract regulation name and madde number from chunk text.

        Returns:
            (regulation_name, madde_number) — both may be None.
        """
        regulation = None
        madde = None

        # Look for regulation name patterns
        reg_patterns = [
            r"([\w\s]+(?:Yönetmeliği|Kanunu|Tebliği|Tüzüğü))",
            r"([\w\s]+(?:Yönetmelik|Kanun|Tebliğ|Tüzük))",
        ]
        for pattern in reg_patterns:
            match = re.search(pattern, chunk_text[:500])
            if match:
                regulation = match.group(1).strip()
                break

        # Look for Madde numbers
        madde_match = re.search(r"[Mm]adde\s+(\d+)", chunk_text)
        if madde_match:
            madde = madde_match.group(1)

        return regulation or fallback_title, madde
