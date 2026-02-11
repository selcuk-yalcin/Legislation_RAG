"""
Web Vector Store - Vectorizes web-sourced chunks and persists them in MongoDB.
Uses the same Voyage-law-2 embeddings as the internal RAG pipeline.

Stores web-fetched documents in a SEPARATE collection (web_search) under
the same mevzuat_db database. This keeps web content isolated from
manually uploaded documents while sharing the same DB.

Flow:
  1st time: Serper → fetch → Azure DI → chunk → Voyage embed → MongoDB (web_search)
  2nd time: URL already in DB → skip Azure DI + Voyage → read from MongoDB directly
"""

import os
from typing import List, Dict, Optional
from datetime import datetime, timezone

import voyageai
from pymongo import MongoClient
from config import (
    MONGO_URI,
    MONGO_DB_NAME,
    VOYAGE_API_KEY,
    VOYAGE_EMBEDDING_MODEL,
)


# ─────────────────────────────────────────────────────────────
# Collection name: "web_search" (aynı mevzuat_db altında)
# documents = manuel yüklenen PDF'ler
# web_search = Serper ile çekilip Azure DI + Voyage ile işlenen
# user_feedback = kullanıcı geri bildirimleri
# ─────────────────────────────────────────────────────────────
WEB_COLLECTION_NAME = os.getenv("WEB_COLLECTION_NAME", "web_search")


class WebVectorStore:
    """
    Vectorizes web-fetched document chunks with Voyage-law-2
    and stores them in mevzuat_db.web_search collection.

    Duplicate check: url_already_stored() prevents re-processing.
    2nd query for same URL → reads directly from MongoDB (zero cost).
    """

    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.collection = self.db[WEB_COLLECTION_NAME]

        if not VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY not set")

        self.voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        self.model = VOYAGE_EMBEDDING_MODEL

        # Ensure indexes for fast lookup
        self.collection.create_index("metadata.source_url")
        self.collection.create_index("metadata.document_title")
        self.collection.create_index("metadata.source_type")

        doc_count = self.collection.count_documents({})
        url_count = len(self.collection.distinct("metadata.source_url"))
        print(f"✅ WebVectorStore initialized (mevzuat_db.{WEB_COLLECTION_NAME})")
        print(f"   📊 {doc_count} chunks, {url_count} unique URLs cached")

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def url_already_stored(self, url: str) -> bool:
        """Check if a URL has already been processed and stored."""
        count = self.collection.count_documents({"metadata.source_url": url})
        if count > 0:
            print(f"   💾 Cache HIT: {url[:60]}... ({count} chunks in DB)")
        return count > 0

    def get_chunks_by_url(self, url: str, limit: int = 20) -> List[Dict]:
        """
        Retrieve all stored chunks for a given URL directly from MongoDB.
        This is the ZERO-COST path — no Azure DI, no Voyage needed.
        """
        docs = list(self.collection.find(
            {"metadata.source_url": url},
            {"content": 1, "metadata": 1, "_id": 0}
        ).limit(limit))
        if docs:
            print(f"   💾 Loaded {len(docs)} cached chunks from DB (zero API cost)")
        return docs

    def store_chunks(self, chunks: List[Dict]) -> int:
        """
        Vectorize and store a list of chunks into MongoDB web_search collection.

        Each chunk gets:
          - content: text content
          - embedding: 1024-dim Voyage-law-2 vector
          - metadata.source_type: "web_search"
          - metadata.source_url: original URL
          - metadata.indexed_at: timestamp
          - metadata.fetcher_method: "serper_azure_voyage"

        Args:
            chunks: Output of WebDocumentChunker.chunk_document()
                    Each item: {content: str, metadata: dict}

        Returns:
            Number of chunks successfully stored.
        """
        if not chunks:
            return 0

        # Duplicate check — skip if URL already stored
        first_url = chunks[0].get("metadata", {}).get("source_url")
        if first_url and self.url_already_stored(first_url):
            print(f"   ⏭️  Skipping store — URL already in DB")
            return 0

        texts = [c["content"] for c in chunks]

        # Vectorize in batches of 32 (Voyage batch limit)
        all_embeddings = []
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                result = self.voyage.embed(batch, model=self.model, input_type="document")
                all_embeddings.extend(result.embeddings)
            except Exception as e:
                print(f"   ❌ Voyage embedding batch {i // batch_size} failed: {e}")
                # Fill with None so indices stay aligned
                all_embeddings.extend([None] * len(batch))

        # Build MongoDB documents
        docs_to_insert = []
        now = datetime.now(timezone.utc).isoformat()

        for idx, chunk in enumerate(chunks):
            emb = all_embeddings[idx] if idx < len(all_embeddings) else None
            if emb is None:
                continue

            metadata = chunk["metadata"].copy()
            metadata["indexed_at"] = now
            metadata["source_type"] = "web_search"
            metadata["fetcher_method"] = "serper_azure_voyage"

            docs_to_insert.append({
                "content": chunk["content"],
                "embedding": emb,
                "metadata": metadata,
            })

        if not docs_to_insert:
            print("   ❌ No embeddings generated — nothing stored")
            return 0

        try:
            result = self.collection.insert_many(docs_to_insert)
            stored = len(result.inserted_ids)
            print(f"   ✅ Stored {stored} web chunks in MongoDB ({WEB_COLLECTION_NAME})")
            return stored
        except Exception as e:
            print(f"   ❌ MongoDB insert failed: {e}")
            return 0

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Vector search over stored web documents.

        Args:
            query: Search query text.
            k: Number of results to return.

        Returns:
            List of {content, metadata, score} dicts.
        """
        try:
            query_emb = self.voyage.embed(
                [query], model=self.model, input_type="query"
            ).embeddings[0]
        except Exception as e:
            print(f"   ❌ Query embedding failed: {e}")
            return []

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "web_vector_index",
                    "path": "embedding",
                    "queryVector": query_emb,
                    "numCandidates": k * 10,
                    "limit": k,
                }
            },
            {
                "$project": {
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            results = list(self.collection.aggregate(pipeline))
            print(f"   ✅ Web vector search returned {len(results)} results")
            return results
        except Exception as e:
            print(f"   ❌ Web vector search failed: {e}")
            return []

    def get_stats(self) -> Dict:
        """Return collection statistics."""
        total = self.collection.count_documents({})
        urls = len(self.collection.distinct("metadata.source_url"))
        return {
            "total_chunks": total,
            "unique_urls": urls,
            "collection": WEB_COLLECTION_NAME,
        }
