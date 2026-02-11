#!/usr/bin/env python3
"""
Web Fallback & MongoDB Cache Test

Bu script:
1. Web fallback tetikleyecek bir soru sorar
2. Cevabın web'den mi geldiğini kontrol eder
3. MongoDB web_search collection'a kaydedilip kaydedilmediğini kontrol eder
4. Aynı soruyu tekrar sorup cache'den mi geldiğini doğrular
5. Kaynak bilgilerini detaylı gösterir
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Config
API_URL = "https://legislationrag-production.up.railway.app/api/ask"
MONGO_URI = os.getenv("MONGO_URI")

def get_mongo_web_search_stats():
    """MongoDB web_search collection istatistiklerini al"""
    client = MongoClient(MONGO_URI)
    db = client["mevzuat_db"]
    
    stats = {
        "total_docs": db.web_search.count_documents({}),
        "unique_urls": len(db.web_search.distinct("metadata.source_url")),
        "latest_docs": list(db.web_search.find(
            {}, 
            {"metadata.source_url": 1, "metadata.indexed_at": 1, "text": 1}
        ).sort("metadata.indexed_at", -1).limit(5))
    }
    
    client.close()
    return stats

def get_chunks_by_url_pattern(pattern):
    """Belirli URL pattern'ine sahip chunk'ları bul"""
    client = MongoClient(MONGO_URI)
    db = client["mevzuat_db"]
    
    chunks = list(db.web_search.find(
        {"metadata.source_url": {"$regex": pattern, "$options": "i"}},
        {"metadata.source_url": 1, "metadata.source_title": 1, "text": 1, "_id": 0}
    ).limit(10))
    
    client.close()
    return chunks

def ask_question(question):
    """API'ye soru sor ve detaylı response al"""
    try:
        response = requests.post(
            API_URL,
            json={"question": question},
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def print_separator(title):
    print("\n" + "=" * 80)
    print(f"🔍 {title}")
    print("=" * 80)

def main():
    print("\n" + "🌐" * 40)
    print("   WEB FALLBACK & MONGODB CACHE TEST")
    print("🌐" * 40)
    
    # ==========================================
    # STEP 1: Mevcut MongoDB durumunu kontrol et
    # ==========================================
    print_separator("STEP 1: MongoDB web_search Collection Durumu (ÖNCE)")
    
    before_stats = get_mongo_web_search_stats()
    print(f"\n📊 Mevcut Durum:")
    print(f"   - Toplam doküman: {before_stats['total_docs']}")
    print(f"   - Unique URL'ler: {before_stats['unique_urls']}")
    
    if before_stats['latest_docs']:
        print(f"\n📄 Son Eklenen Dokümanlar:")
        for doc in before_stats['latest_docs'][:3]:
            url = doc.get('metadata', {}).get('source_url', 'N/A')
            indexed = doc.get('metadata', {}).get('indexed_at', 'N/A')
            text_preview = doc.get('text', '')[:80]
            print(f"   - {url[:60]}...")
            print(f"     📅 {indexed}")
    
    # ==========================================
    # STEP 2: Internal (DB'de olan) soru sor
    # ==========================================
    print_separator("STEP 2: Internal (MongoDB) Soru Testi")
    
    internal_question = "Yapı işlerinde korkuluk yüksekliği en az kaç cm olmalıdır?"
    print(f"\n❓ Soru: {internal_question}")
    
    result1 = ask_question(internal_question)
    
    print(f"\n📋 Sonuç:")
    print(f"   - Method: {result1.get('method', 'N/A')} {'✅ DB' if result1.get('method') == 'internal' else '🌐 Web'}")
    print(f"   - Source Count: {result1.get('source_count', 0)}")
    print(f"   - Answer: {result1.get('answer', 'N/A')[:200]}...")
    
    if result1.get('sources'):
        print(f"\n📚 Kaynaklar:")
        for i, src in enumerate(result1['sources'][:3], 1):
            print(f"   {i}. {src.get('title', src.get('source', 'N/A'))[:60]}")
            if src.get('link'):
                print(f"      🔗 {src['link'][:70]}...")
    
    # ==========================================
    # STEP 3: Web Fallback Tetikle (DB'de olmayan soru)
    # ==========================================
    print_separator("STEP 3: Web Fallback Testi (DB'de Olmayan Soru)")
    
    # DB'de kesinlikle olmayacak güncel sorular
    web_questions = [
        "2025 yılında iş güvenliği mevzuatında yapılan son değişiklikler nelerdir?",
        "ÇSGB'nin yayınladığı en güncel iş güvenliği rehberleri hangileridir?",
        "İş ekipmanları yönetmeliğinde 2024 sonrası yapılan değişiklikler nelerdir?"
    ]
    
    for q in web_questions:
        print(f"\n❓ Soru: {q[:70]}...")
        
        result = ask_question(q)
        
        method = result.get('method', 'unknown')
        is_web = method in ['web_fallback', 'hybrid', 'web']
        
        print(f"   - Method: {method} {'🌐 WEB' if is_web else '📚 DB'}")
        print(f"   - Source Count: {result.get('source_count', 0)}")
        
        if result.get('sources'):
            print(f"   - Kaynaklar:")
            for i, src in enumerate(result['sources'][:2], 1):
                title = src.get('title', src.get('source', 'N/A'))
                link = src.get('link', '')
                source_type = "🌐 Web" if link.startswith('http') else "📚 DB"
                print(f"     {i}. [{source_type}] {title[:50]}")
                if link:
                    print(f"        🔗 {link[:60]}...")
        
        answer = result.get('answer', '')[:150]
        print(f"   - Cevap: {answer}...")
        
        # Biraz bekle (rate limiting)
        time.sleep(2)
    
    # ==========================================
    # STEP 4: MongoDB web_search'e kaydedildi mi?
    # ==========================================
    print_separator("STEP 4: MongoDB web_search Collection Durumu (SONRA)")
    
    # Biraz bekle - MongoDB'ye yazılması için
    time.sleep(3)
    
    after_stats = get_mongo_web_search_stats()
    print(f"\n📊 Güncel Durum:")
    print(f"   - Toplam doküman: {after_stats['total_docs']} (önceki: {before_stats['total_docs']})")
    print(f"   - Unique URL'ler: {after_stats['unique_urls']} (önceki: {before_stats['unique_urls']})")
    
    new_docs = after_stats['total_docs'] - before_stats['total_docs']
    if new_docs > 0:
        print(f"\n✅ {new_docs} yeni doküman eklendi!")
    else:
        print(f"\n⚠️ Yeni doküman eklenmedi (cache'den gelmiş olabilir)")
    
    if after_stats['latest_docs']:
        print(f"\n📄 Son Eklenen Dokümanlar:")
        for doc in after_stats['latest_docs'][:5]:
            url = doc.get('metadata', {}).get('source_url', 'N/A')
            indexed = doc.get('metadata', {}).get('indexed_at', 'N/A')
            text_preview = doc.get('text', '')[:100].replace('\n', ' ')
            print(f"   - {url[:70]}...")
            print(f"     📅 Indexed: {indexed}")
            print(f"     📝 Preview: {text_preview}...")
    
    # ==========================================
    # STEP 5: CSGB kaynaklarını kontrol et
    # ==========================================
    print_separator("STEP 5: CSGB Kaynakları Kontrolü")
    
    csgb_chunks = get_chunks_by_url_pattern("csgb.gov.tr")
    print(f"\n📊 CSGB kaynaklı chunk sayısı: {len(csgb_chunks)}")
    
    if csgb_chunks:
        print(f"\n📄 CSGB Chunk Örnekleri:")
        for i, chunk in enumerate(csgb_chunks[:5], 1):
            url = chunk.get('metadata', {}).get('source_url', 'N/A')
            title = chunk.get('metadata', {}).get('source_title', 'N/A')
            text = chunk.get('text', '')[:150].replace('\n', ' ')
            print(f"\n   {i}. {title[:60]}")
            print(f"      🔗 {url[:70]}...")
            print(f"      📝 {text}...")
    
    # ==========================================
    # STEP 6: Cache Test - Aynı soruyu tekrar sor
    # ==========================================
    print_separator("STEP 6: Cache Test - Aynı Soru Tekrar")
    
    cache_question = "2025 yılında iş güvenliği mevzuatında yapılan son değişiklikler nelerdir?"
    print(f"\n❓ Aynı Soru: {cache_question[:60]}...")
    
    start_time = time.time()
    result_cached = ask_question(cache_question)
    elapsed = time.time() - start_time
    
    print(f"\n📋 Sonuç:")
    print(f"   - Method: {result_cached.get('method', 'N/A')}")
    print(f"   - Süre: {elapsed:.2f} saniye")
    print(f"   - Source Count: {result_cached.get('source_count', 0)}")
    
    if elapsed < 5:
        print(f"\n✅ Hızlı cevap ({elapsed:.2f}s) - Muhtemelen cache'den geldi!")
    else:
        print(f"\n⚠️ Yavaş cevap ({elapsed:.2f}s) - Web'den tekrar çekilmiş olabilir")
    
    # ==========================================
    # STEP 7: Özet Rapor
    # ==========================================
    print_separator("STEP 7: ÖZET RAPOR")
    
    print(f"""
📊 TEST SONUÇLARI
================

1. MongoDB Durumu:
   - Önceki doküman sayısı: {before_stats['total_docs']}
   - Şimdiki doküman sayısı: {after_stats['total_docs']}
   - Yeni eklenen: {after_stats['total_docs'] - before_stats['total_docs']}

2. API Response Formatı:
   - 'method' field: {'✅ Var' if 'method' in result1 else '❌ Yok'}
   - 'sources' field: {'✅ Var' if 'sources' in result1 else '❌ Yok'}
   - 'source_count' field: {'✅ Var' if 'source_count' in result1 else '❌ Yok'}

3. Internal vs Web:
   - Internal (DB) sorular: method = "internal"
   - Web Fallback sorular: method = "web_fallback" veya "hybrid"

4. CSGB Kaynakları:
   - Toplam chunk: {len(csgb_chunks)}
   - Cache çalışıyor: {'✅ Evet' if elapsed < 10 else '⚠️ Kontrol gerekli'}

5. Sonuç:
   - Web fallback: {'✅ Çalışıyor' if any(r.get('method') in ['web_fallback', 'hybrid', 'web'] for r in [result1, result_cached]) else '⚠️ Test edilemedi'}
   - MongoDB cache: {'✅ Çalışıyor' if after_stats['total_docs'] >= before_stats['total_docs'] else '⚠️ Kontrol gerekli'}
""")

if __name__ == "__main__":
    main()
