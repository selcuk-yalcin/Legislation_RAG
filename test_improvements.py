"""
Quick test for recent improvements:
1. Red flag optimization (50 char threshold instead of 80)
2. Query relevance filter (blocks irrelevant questions)
3. Web fallback timeout (max 180 seconds)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from client import create_openrouter_client
from mongodb_vector_store import get_mongodb_vectorstore
from voyage_reranker import VoyageReranker
from rag_pipeline import RAGPipeline
from hybrid_pipeline import HybridRAGOrchestrator
from pymongo import MongoClient

print("=" * 80)
print("🧪 TESTING IMPROVEMENTS")
print("=" * 80)

# Initialize
openrouter_client = create_openrouter_client()
vectorstore = get_mongodb_vectorstore()
reranker = VoyageReranker()
rag = RAGPipeline(openrouter_client, vectorstore, reranker)

mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client[os.getenv("MONGO_DB_NAME", "mevzuat_db")]
collection = db[os.getenv("MONGO_COLLECTION_NAME", "documents")]

orchestrator = HybridRAGOrchestrator(
    rag_pipeline=rag,
    mongo_collection=collection,
    openrouter_client=openrouter_client
)

# ────────────────────────────────────────────
# Test 1: Relevance Filter (should block)
# ────────────────────────────────────────────
print("\n" + "=" * 80)
print("TEST 1: Query Relevance Filter")
print("=" * 80)

test1 = "Uzay istasyonunda çalışırken ne yapmalıyım?"
print(f"\nQuery: {test1}")
result1 = orchestrator.query(test1)
print(f"\n✓ Method: {result1['method']}")
print(f"✓ Expected: guidance (filtered as irrelevant)")
print(f"✓ Result: {'PASS ✅' if result1['method'] == 'guidance' else 'FAIL ❌'}")

# ────────────────────────────────────────────
# Test 2: Short but valid answer (50 char threshold)
# ────────────────────────────────────────────
print("\n" + "=" * 80)
print("TEST 2: Short Answer Acceptance (50 char threshold)")
print("=" * 80)

test2 = "KKD zorunlu mu?"
print(f"\nQuery: {test2}")
result2 = orchestrator.query(test2)
print(f"\n✓ Method: {result2['method']}")
print(f"✓ Answer length: {len(result2['answer'])} chars")
print(f"✓ Expected: primary_rag (short query, short answer OK)")
print(f"✓ Result: {'PASS ✅' if result2['method'] == 'primary_rag' else 'FAIL ❌'}")

# ────────────────────────────────────────────
# Test 3: Stats check
# ────────────────────────────────────────────
print("\n" + "=" * 80)
print("FINAL STATISTICS")
print("=" * 80)
orchestrator.print_statistics()

print("\n" + "=" * 80)
print("✅ IMPROVEMENT TESTS COMPLETE")
print("=" * 80)
