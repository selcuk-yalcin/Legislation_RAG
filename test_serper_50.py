"""
Comprehensive Serper Web Search Test - 50 Questions
Tests Serper.dev API with diverse ISG (Occupational Health & Safety) queries
and logs all results to a file for analysis.
"""

import os
import json
from datetime import datetime
from web_search import SerperWebSearch


# 50 diverse test questions covering various ISG topics
TEST_QUERIES = [
    # Original 7 questions
    "İş Sağlığı ve Güvenliği Kanunu Madde 4",
    "Yapı İşlerinde İSG Yönetmeliği güncel",
    "6331 sayılı kanun değişiklik",
    "asansör bakım yönetmeliği 2025",
    "yüksekte çalışma korkuluk yüksekliği",
    "kimyasalların olduğu alanlarda elektrik sistemlerinin exproof özellikte olması hangi mevzuatta geçiyor",
    "ilkyardımcı sertifikası kaç yıl geçerli",
    
    # Safety equipment questions (8-15)
    "kişisel koruyucu donanım kullanma zorunluluğu",
    "güvenlik başlığı kullanma şartları",
    "emniyet kemeri kullanım alanları",
    "iş eldiveni seçim kriterleri",
    "gözlük koruma ekipmanları standartları",
    "iş ayakkabısı özellikleri neler olmalı",
    "solunum koruyucu maskelerin sınıflandırması",
    "kulak koruyucu donanım kullanım yerleri",
    
    # Work environment questions (16-25)
    "işyeri aydınlatma standartları",
    "gürültü maruziyeti limit değerleri",
    "işyeri havalandırma gereksinimleri",
    "titreşim maruziyeti sınır değerleri",
    "termal konfor koşulları",
    "ergonomik çalışma ortamı düzenlemesi",
    "ofis çalışma ortamı standartları",
    "elektrik panosu güvenlik mesafeleri",
    "acil durum aydınlatma gereksinimleri",
    "yangın söndürme tüpü konumlandırma",
    
    # Training and certification (26-33)
    "iş güvenliği uzmanı sertifikası geçerlilik süresi",
    "işyeri hekimi görevlendirilme şartları",
    "yangın eğitimi periyodu",
    "forklift sertifikası geçerlilik süresi",
    "iş ekipmanı operatör belgesi",
    "elektrikli el aletleri kullanım eğitimi",
    "acil durum tatbikatı yapma sıklığı",
    "kimyasal güvenlik bilgi formu eğitimi",
    
    # Inspections and audits (34-41)
    "iş ekipmanı periyodik kontrol süresi",
    "iskele periyodik kontrol gereksinimleri",
    "kaldırma ekipmanları muayene periyodu",
    "kompresör tank kontrol sıklığı",
    "basınçlı kaplar muayene standartları",
    "kule vinç periyodik kontrol",
    "mobil kule periyodik kontrol süresi",
    "elektrik tesisatı topraklama ölçümü",
    
    # Specific regulations (42-50)
    "gece çalışması düzenlemeleri",
    "hamile çalışan koruma önlemleri",
    "genç işçi çalıştırma yaş sınırı",
    "ağır ve tehlikeli işler yönetmeliği",
    "maden işyerleri özel düzenlemeler",
    "tersanelerde isg uygulamaları",
    "taş ocakları isg yönetmeliği",
    "patlayıcı ortamlar atex direktifi",
    "iş kazası bildirim süresi"
]


def test_serper_comprehensive():
    """
    Test Serper.dev with 50 diverse ISG questions.
    Logs all results to serper_test_results.json
    """
    
    # Set API key
    os.environ["SERPER_API_KEY"] = "06f0eda33581aa5c10f2b90dec87062cd7ce64e9"
    
    print("=" * 80)
    print("🧪 SERPER COMPREHENSIVE TEST - 50 ISG QUESTIONS")
    print("=" * 80)
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Total Questions: {len(TEST_QUERIES)}")
    print("=" * 80)
    print()
    
    # Initialize search engine
    try:
        search = SerperWebSearch()
    except Exception as e:
        print(f"❌ Failed to initialize SerperWebSearch: {e}")
        return
    
    # Results storage
    test_results = {
        "test_date": datetime.now().isoformat(),
        "total_queries": len(TEST_QUERIES),
        "results": []
    }
    
    success_count = 0
    fail_count = 0
    total_results = 0
    
    # Test each query
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(TEST_QUERIES)}] {query}")
        print("=" * 80)
        
        query_result = {
            "query_id": i,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "results": [],
            "error": None
        }
        
        try:
            results = search.search(query, max_results=3)
            
            if results:
                success_count += 1
                total_results += len(results)
                query_result["success"] = True
                query_result["result_count"] = len(results)
                
                print(f"✅ Found {len(results)} results\n")
                
                for idx, result in enumerate(results, 1):
                    result_data = {
                        "rank": idx,
                        "title": result['title'],
                        "url": result['link'],
                        "snippet": result['snippet'][:150] + "...",
                        "date": result.get('date', 'N/A')
                    }
                    query_result["results"].append(result_data)
                    
                    print(f"   [{idx}] {result['title']}")
                    print(f"       📎 {result['link']}")
                    print(f"       💬 {result['snippet'][:100]}...")
                    if result.get('date'):
                        print(f"       📅 {result['date']}")
                    print()
            else:
                fail_count += 1
                query_result["result_count"] = 0
                print("   ⚠️  No results found")
        
        except Exception as e:
            fail_count += 1
            query_result["error"] = str(e)
            print(f"   ❌ Search failed: {e}")
        
        test_results["results"].append(query_result)
        
        # Progress indicator
        if i % 10 == 0:
            print(f"\n{'─'*80}")
            print(f"📊 Progress: {i}/{len(TEST_QUERIES)} ({i*100//len(TEST_QUERIES)}%)")
            print(f"   ✅ Success: {success_count} | ❌ Failed: {fail_count}")
            print(f"{'─'*80}")
    
    # Save results to JSON file
    output_file = "serper_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Successful Queries: {success_count}/{len(TEST_QUERIES)} ({success_count*100//len(TEST_QUERIES)}%)")
    print(f"❌ Failed Queries: {fail_count}/{len(TEST_QUERIES)}")
    print(f"📄 Total Results Found: {total_results}")
    print(f"📈 Avg Results per Query: {total_results/success_count if success_count > 0 else 0:.2f}")
    print(f"💾 Results saved to: {output_file}")
    print("=" * 80)
    
    # Category breakdown
    print("\n📋 QUERY CATEGORY BREAKDOWN:")
    print("-" * 80)
    print("1. Original Questions: 1-7")
    print("2. Safety Equipment: 8-15")
    print("3. Work Environment: 16-25")
    print("4. Training & Certification: 26-33")
    print("5. Inspections & Audits: 34-41")
    print("6. Specific Regulations: 42-50")
    print("=" * 80)


if __name__ == "__main__":
    test_serper_comprehensive()
