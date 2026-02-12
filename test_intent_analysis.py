#!/usr/bin/env python3
"""
Test script for Intent Analysis (Step 1)
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
from query_expansion import analyze_query_context

load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Test queries
test_queries = [
    "Gece çalışması şartları nelerdir?",  # Genel
    "Madenlerde havalandırma sistemi nasıl olmalı?",  # Maden
    "Gemilerde can yeleği sayısı kaç olmalı?",  # Gemi
    "İnşaat şantiyesinde iskele güvenliği nasıl sağlanır?",  # İnşaat
    "İşveren risk değerlendirmesi yapmak zorunda mı?",  # Genel
]

print("=" * 80)
print("ADIM 1 - NİYET ANALİZİ TESTİ")
print("=" * 80)

for i, query in enumerate(test_queries, 1):
    print(f"\n[{i}/{len(test_queries)}] TEST SORGU: '{query}'")
    print("-" * 80)
    
    result = analyze_query_context(client, query)
    
    print(f"\n📊 SONUÇ:")
    print(f"   Primary Sector: {result.get('primary_sector')}")
    print(f"   Is General: {result.get('is_general')}")
    print(f"   Sectors: {result.get('sectors')}")
    print(f"   Exclude: {result.get('exclude_keywords')}")
    print(f"   Confidence: {result.get('confidence')}")
    print("")

print("=" * 80)
print("✅ ADIM 1 TEST TAMAMLANDI")
print("=" * 80)
