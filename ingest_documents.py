"""
CRM Digital FTE — Document Ingestion Script

Usage:
    python ingest_documents.py docs/                     # All .md files in directory
    python ingest_documents.py context/product-docs.md   # Single file
    python ingest_documents.py .                          # All .md in current dir

Pipeline:
    Read file → Split into chunks → embed_texts() → store_document_chunk() → pgvector
"""

import os
import sys
import json
import re
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ingest")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "agent"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from db.database import CRMDatabase
from embeddings import embed_texts

CHUNK_BATCH_SIZE = 20  # embeddings API batch limit


def find_markdown_files(path: str) -> list[str]:
    """Return all .md files from path (file or directory)."""
    if os.path.isfile(path):
        return [path] if path.endswith(".md") else []
    md_files = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))
    return sorted(md_files)


def chunk_markdown(filepath: str) -> list[dict]:
    """Split a markdown file into chunks by ## headings.

    Returns list of {document_title, chunk_index, content, metadata}.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(filepath)
    # Split on ## headings
    sections = re.split(r"\n(?=## )", content)
    chunks = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n")
        # First line is the heading (strip leading ## )
        title = lines[0].lstrip("#").strip() if lines else filename
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        if not body:
            continue

        # Skip very short chunks (likely just a heading with no content)
        if len(body) < 20:
            continue

        chunks.append({
            "document_title": title,
            "chunk_index": i,
            "content": body,
            "metadata": {
                "source_file": filename,
                "heading": title,
                "total_chunks": len(sections),
            },
        })

    return chunks


def ingest_file(filepath: str, db: CRMDatabase) -> int:
    """Ingest a single markdown file — returns number of chunks stored."""
    chunks = chunk_markdown(filepath)
    if not chunks:
        logger.warning("  No chunks found in %s", filepath)
        return 0

    logger.info("  %d chunks to embed", len(chunks))

    # Collect all texts for batch embedding
    texts = [c["content"] for c in chunks]

    # Embed in batches
    all_embeddings = []
    for start in range(0, len(texts), CHUNK_BATCH_SIZE):
        batch = texts[start: start + CHUNK_BATCH_SIZE]
        logger.info("    Embedding batch %d/%d ...", start // CHUNK_BATCH_SIZE + 1,
                     (len(texts) - 1) // CHUNK_BATCH_SIZE + 1)
        embs = embed_texts(batch)
        if embs is None:
            logger.error("Embedding API failed — check OPENAI_API_KEY in .env")
            return 0
        all_embeddings.extend(embs)
        time.sleep(0.5)  # rate limiting

    # Store in database
    stored = 0
    for chunk, embedding in zip(chunks, all_embeddings):
        db.store_document_chunk(
            document_title=chunk["document_title"],
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            embedding=embedding,
            metadata=chunk["metadata"],
        )
        stored += 1

    return stored


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = sys.argv[1]
    if not os.path.exists(target):
        logger.error("Path not found: %s", target)
        sys.exit(1)

    # Initialize database
    db = CRMDatabase()

    # Find files
    md_files = find_markdown_files(target)
    if not md_files:
        logger.error("No .md files found in: %s", target)
        sys.exit(1)

    logger.info("Found %d markdown file(s)", len(md_files))

    total_stored = 0
    for filepath in md_files:
        logger.info("Ingesting: %s", filepath)
        stored = ingest_file(filepath, db)
        total_stored += stored
        logger.info("  Stored %d chunk(s)", stored)

    count = db.get_document_chunk_count()
    logger.info("")
    logger.info("=" * 50)
    logger.info("INGESTION COMPLETE")
    logger.info("  Files processed: %d", len(md_files))
    logger.info("  Chunks stored:   %d", total_stored)
    logger.info("  Total in DB:     %d", count)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
