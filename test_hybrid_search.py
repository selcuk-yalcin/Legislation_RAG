"""
Test Hybrid MongoDB Vector Search
Tests searching in BOTH documents and web_search collections
"""

from dotenv import load_dotenv
load_dotenv()

from mongodb_vector_store import MongoDBVectorStore

print("=" * 70)
print("HYBRID MONGODB VECTOR SEARCH TEST")
print("=" * 70)

# Initialize
store = MongoDBVectorStore()

# Test query - ISG related
test_query = "kişisel koruyucu donanım gereksinimleri"
print(f"\n🧪 Test Query: '{test_query}'")

# Search with hybrid mode (default: search_web=True)
print("\n" + "=" * 70)
print("TEST 1: HYBRID SEARCH (documents + web_search)")
print("=" * 70)
results = store.similarity_search(test_query, k=10, search_web=True)

print(f"\n📊 Results: {len(results)}")
for i, doc in enumerate(results[:5], 1):
    source_type = doc.metadata.get('source_type', 'unknown')
    title = doc.metadata.get('document_title', 'No title')[:60]
    score = getattr(doc, 'score', 0)
    print(f"  {i}. [{source_type:12s}] {score:.4f} | {title}")

# Count by source type
from collections import Counter
source_counts = Counter(doc.metadata.get('source_type', 'unknown') for doc in results)
print(f"\n📈 Source Distribution:")
for source, count in source_counts.items():
    print(f"   {source}: {count}")

# Test without web search
print("\n" + "=" * 70)
print("TEST 2: DOCUMENTS ONLY (search_web=False)")
print("=" * 70)
docs_only = store.similarity_search(test_query, k=10, search_web=False)
print(f"\n📊 Results: {len(docs_only)} (all from 'documents' collection)")

print("\n" + "=" * 70)
print("✅ HYBRID SEARCH TEST COMPLETE")
print("=" * 70)
print(f"""
SUMMARY:
  Hybrid Search:      {len(results)} results
  Documents Only:     {len(docs_only)} results
  Web Results:        {source_counts.get('web_search', 0)}
  Manual Results:     {len(results) - source_counts.get('web_search', 0)}
  
💡 Internal RAG now searches BOTH collections automatically!
""")
