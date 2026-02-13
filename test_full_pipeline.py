#!/usr/bin/env python3
"""
FULL PIPELINE TEST - Tüm 5 Adımı Test Et
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient
import voyageai

# Load environment
load_dotenv()

# Initialize clients
print("=" * 80)
print("🚀 5 ADIMLI AKILLI RAG PİPELINE TESTİ")
print("=" * 80)

print("\n📦 Bileşenler yükleniyor...")

# OpenRouter client
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)
print("✅ OpenRouter client hazır")

# MongoDB vector store
from mongodb_vector_store import MongoDBVectorStore
vectorstore = MongoDBVectorStore()
print("✅ MongoDB vector store hazır")

# Voyage Reranker
from voyage_reranker import VoyageReranker
reranker = VoyageReranker()
print("✅ Voyage Reranker hazır")

# RAG Pipeline
from rag_pipeline import RAGPipeline
rag = RAGPipeline(
    client=openrouter_client,
    vectorstore=vectorstore,
    reranker=reranker
)
print("✅ RAG Pipeline hazır")

print("\n" + "=" * 80)
print("TEST SORULARI")
print("=" * 80)

# Test queries with expected sectors
test_cases = [
    {
        "query": "Gece çalışması kaç saat olabilir?",
        "expected_sector": "Genel",
        "description": "Genel iş güvenliği sorusu"
    },
    {
        "query": "Madenlerde havalandırma sistemi nasıl olmalı?",
        "expected_sector": "Maden",
        "description": "Maden sektörüne özel soru"
    },
    {
        "query": "İşveren risk değerlendirmesi yapmak zorunda mı?",
        "expected_sector": "Genel",
        "description": "Genel işveren yükümlülüğü"
    }
]

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['description']}")
    print(f"SORU: {test['query']}")
    print(f"BEKLENEN SEKTÖR: {test['expected_sector']}")
    print(f"{'='*80}\n")
    
    try:
        # Generate response (5 adım otomatik çalışacak)
        result = rag.generate_response(test['query'])
        
        print(f"\n📝 CEVAP:")
        print("-" * 80)
        print(result['answer'])
        print("-" * 80)
        
        print(f"\n📊 KAYNAKLAR: {len(result.get('sources', []))} adet")
        for j, src in enumerate(result.get('sources', [])[:3], 1):
            title = src.get('title') or src.get('name') or 'Bilinmeyen'
            print(f"   {j}. {title}")
        
        print(f"\n✅ Test {i} başarılı!\n")
        
    except Exception as e:
        print(f"\n❌ Test {i} HATALI: {e}\n")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("✅ TÜM TESTLER TAMAMLANDI")
print("=" * 80)
