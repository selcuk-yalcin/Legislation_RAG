"""
Test Hybrid RAG with OpenRouter Gemini 2.0 Flash
"""

import os
from pymongo import MongoClient
from client import create_openrouter_client
from mongodb_vector_store import MongoDBVectorStore
from voyage_reranker import VoyageReranker
from rag_pipeline import RAGPipeline
from hybrid_pipeline import HybridRAGOrchestrator

print("=" * 80)
print("🧪 HYBRID RAG TEST - OpenRouter Gemini 2.0 Flash")
print("=" * 80)

# 1. MongoDB bağlantısı
print("\n1️⃣  Connecting to MongoDB...")
vectorstore = MongoDBVectorStore()
stats = vectorstore.get_collection_stats()
print(f"   ✅ {stats['total_documents']:,} documents loaded")

# 2. OpenRouter client (GPT-4o-mini için RAG + Gemini 2.0 Flash için fallback)
print("\n2️⃣  Initializing OpenRouter client...")
openrouter_client = create_openrouter_client()
print("   ✅ OpenRouter client ready")

# 3. Reranker
print("\n3️⃣  Initializing Voyage reranker...")
reranker = VoyageReranker()
print("   ✅ Voyage reranker ready")

# 4. RAG Pipeline
print("\n4️⃣  Creating RAG pipeline...")
rag_pipeline = RAGPipeline(openrouter_client, vectorstore, reranker)
print("   ✅ RAG pipeline ready")

# 5. Hybrid Orchestrator
print("\n5️⃣  Creating Hybrid Orchestrator...")
orchestrator = HybridRAGOrchestrator(
    rag_pipeline=rag_pipeline,
    mongo_collection=vectorstore.collection,
    openrouter_client=openrouter_client,
    enable_fallback=True
)
print("   ✅ Hybrid orchestrator ready")

print("\n" + "=" * 80)
print("🎯 TESTING QUERIES")
print("=" * 80)

# Test 1: Easy question (should use RAG)
print("\n📝 TEST 1: Easy question (expect RAG)")
query1 = "İş güvenliği uzmanlarının çalışma süreleri nedir?"
result1 = orchestrator.query(query1)
print(f"   • Method: {result1['method']}")
print(f"   • Confidence: {result1['confidence']:.2f}")
print(f"   • Answer preview: {result1['answer'][:100]}...")

# Test 2: Harder question (might trigger Gemini)
print("\n📝 TEST 2: Complex question (may trigger Gemini)")
query2 = "Patlayıcı ortamda kullanılan ekipmanların tüm teknik şartları nelerdir?"
result2 = orchestrator.query(query2)
print(f"   • Method: {result2['method']}")
print(f"   • Confidence: {result2['confidence']:.2f}")
print(f"   • Answer preview: {result2['answer'][:100]}...")

# Test 3: Force fallback
print("\n📝 TEST 3: Forced Gemini fallback")
result3 = orchestrator.query(query1, force_fallback=True)
print(f"   • Method: {result3['method']}")
print(f"   • Regulation: {result3.get('regulation', 'N/A')}")
print(f"   • Model: {result3.get('model', 'N/A')}")
print(f"   • Answer preview: {result3['answer'][:100]}...")

# Statistics
print("\n" + "=" * 80)
print("📊 STATISTICS")
print("=" * 80)
orchestrator.print_statistics()

print("\n✅ All tests completed!")
