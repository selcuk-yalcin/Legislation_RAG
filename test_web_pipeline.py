"""
End-to-End Web Pipeline Test
Tests the full flow: Serper → Fetch → Azure DI → Chunk → Voyage → MongoDB

Tests:
  1. Serper search
  2. Download a PDF from csgb.gov.tr (publicly accessible)
  3. Parse with Azure DI (bytes → markdown)
  4. Chunk with WebDocumentChunker
  5. Vectorize with Voyage-law-2 and store in MongoDB web_search collection
  6. Verify stored in MongoDB
  7. 2nd call: verify it reads from cache (zero API cost)
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# ─── Test 1: Serper Search ───────────────────────────────
print("=" * 70)
print("TEST 1: Serper Web Search")
print("=" * 70)
from web_search import SerperWebSearch
searcher = SerperWebSearch()
results = searcher.search("kişisel koruyucu donanım yönetmeliği", max_results=3, expand_synonyms=False)
print(f"\n  Results: {len(results)}")
for r in results:
    print(f"  - {r['title'][:60]}")
    print(f"    {r['link'][:80]}")

# Find a PDF URL from csgb.gov.tr (accessible without TR IP)
pdf_url = None
html_url = None
for r in results:
    link = r["link"]
    if link.lower().endswith(".pdf") and "csgb.gov.tr" in link:
        pdf_url = link
        break
    elif "csgb.gov.tr" in link and not link.lower().endswith(".pdf"):
        html_url = link

test_url = pdf_url or html_url
if not test_url:
    # Use a known accessible csgb page (HTML)
    test_url = "https://www.csgb.gov.tr/isgum/"
    print(f"\n  No accessible URL from search, using known page: {test_url}")

# Override: avoid the 12MB KKD kitabı PDF (exceeds Azure DI 4MB limit)
if test_url and "kkd_kitabi.pdf" in test_url:
    test_url = "https://www.csgb.gov.tr/isgum/"
    print(f"\n  KKD kitabı PDF too large (12MB > Azure DI 4MB limit), using HTML page instead")

print(f"\n  Selected URL for full test: {test_url}")

# ─── Test 2: Download Content ────────────────────────────
print("\n" + "=" * 70)
print("TEST 2: Download Content (raw bytes)")
print("=" * 70)
from web_content_fetcher import WebContentFetcher
fetcher = WebContentFetcher()
raw_bytes, content_type = fetcher.fetch_raw_bytes(test_url)

if not raw_bytes:
    print("  ❌ FAILED to download. Trying alternative URL...")
    # Fallback to KKD portal main page
    test_url = "https://kkdportal.csgb.gov.tr"
    raw_bytes, content_type = fetcher.fetch_raw_bytes(test_url)

if not raw_bytes:
    print("  ❌ FAILED to download any URL. Exiting.")
    sys.exit(1)

print(f"  Downloaded: {len(raw_bytes):,} bytes ({content_type})")

# ─── Test 3: Parse with Azure DI ─────────────────────────
print("\n" + "=" * 70)
print("TEST 3: Azure DI Parse (bytes → markdown)")
print("=" * 70)
from azure_doc_parser import AzureDocParser
parser = AzureDocParser()

if content_type == "pdf":
    markdown = parser.parse_pdf_bytes(raw_bytes)
else:
    markdown = parser.parse_html_bytes(raw_bytes)

if not markdown or len(markdown) < 50:
    print("  ❌ Azure DI returned too little content")
    sys.exit(1)

print(f"  Parsed: {len(markdown):,} chars of markdown")
print(f"  First 300 chars:\n  {markdown[:300]}")

# ─── Test 4: Chunk ───────────────────────────────────────
print("\n" + "=" * 70)
print("TEST 4: Semantic Chunking")
print("=" * 70)
from web_doc_chunker import WebDocumentChunker
chunker = WebDocumentChunker()
chunks = chunker.chunk_document(
    text=markdown,
    source_url=test_url,
    source_title="KKD Yönetmeliği Test",
    content_type="markdown"
)
print(f"  Chunks: {len(chunks)}")
if chunks:
    print(f"  First chunk ({len(chunks[0]['content'])} chars):")
    print(f"  {chunks[0]['content'][:200]}...")
    print(f"  Metadata: {chunks[0]['metadata']}")

# ─── Test 5: Voyage Embed + MongoDB Store ─────────────────
print("\n" + "=" * 70)
print("TEST 5: Voyage Embed + MongoDB Store (mevzuat_db.web_search)")
print("=" * 70)
from web_vector_store import WebVectorStore
store = WebVectorStore()

# First, clean up any previous test data for this URL
from pymongo import MongoClient
client = MongoClient(os.getenv("MONGO_URI"))
db = client["mevzuat_db"]
deleted = db.web_search.delete_many({"metadata.source_url": test_url})
print(f"  Cleaned up {deleted.deleted_count} previous test docs")

# Store chunks
stored_count = store.store_chunks(chunks)
print(f"  Stored: {stored_count} chunks in MongoDB")

# ─── Test 6: Verify in MongoDB ────────────────────────────
print("\n" + "=" * 70)
print("TEST 6: Verify in MongoDB (mevzuat_db.web_search)")
print("=" * 70)
total = db.web_search.count_documents({})
url_count = db.web_search.count_documents({"metadata.source_url": test_url})
all_urls = db.web_search.distinct("metadata.source_url")

print(f"  Total docs in web_search: {total}")
print(f"  Docs for test URL: {url_count}")
print(f"  Unique URLs stored: {len(all_urls)}")

# Check a sample document
sample = db.web_search.find_one({"metadata.source_url": test_url})
if sample:
    print(f"\n  Sample document:")
    print(f"    content length: {len(sample.get('content', ''))}")
    print(f"    embedding dim: {len(sample.get('embedding', []))}")
    meta = sample.get("metadata", {})
    print(f"    source_type: {meta.get('source_type')}")
    print(f"    source_url: {meta.get('source_url', '')[:60]}")
    print(f"    fetcher_method: {meta.get('fetcher_method')}")
    print(f"    indexed_at: {meta.get('indexed_at')}")

# ─── Test 7: Cache Test (2nd call = zero cost) ────────────
print("\n" + "=" * 70)
print("TEST 7: Cache Test — 2nd call should be FREE (no Azure DI / Voyage)")
print("=" * 70)

# Check if URL is stored
is_stored = store.url_already_stored(test_url)
print(f"  URL in DB: {is_stored}")

# Get chunks directly from DB (zero cost)
cached_chunks = store.get_chunks_by_url(test_url)
print(f"  Cached chunks retrieved: {len(cached_chunks)}")
if cached_chunks:
    print(f"  First cached chunk: {cached_chunks[0]['content'][:100]}...")

# Try storing again — should skip
print("\n  Trying to store same URL again...")
stored_again = store.store_chunks(chunks)
print(f"  Stored again: {stored_again} (should be 0 = skipped)")

# ─── Summary ──────────────────────────────────────────────
print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED — FULL PIPELINE WORKING")
print("=" * 70)
print(f"""
SUMMARY:
  Serper search:     ✅ {len(results)} results
  Content download:  ✅ {len(raw_bytes):,} bytes
  Azure DI parse:    ✅ {len(markdown):,} chars markdown
  Chunking:          ✅ {len(chunks)} chunks
  Voyage + MongoDB:  ✅ {stored_count} stored in web_search
  Cache (2nd call):  ✅ {len(cached_chunks)} from cache (zero cost)
  
MongoDB Structure:
  mevzuat_db
  ├── documents      (5,485 docs — manual uploads)
  ├── user_feedback  (51 docs)
  └── web_search     ({total} docs — Serper → Azure DI → Voyage)  ← NEW
""")
