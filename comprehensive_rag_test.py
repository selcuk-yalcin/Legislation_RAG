#!/usr/bin/env python3
"""
KAPSAMLI RAG TEST SUITe
=======================
Bu script hem internal (MongoDB) hem de web fallback (Serper) kaynaklarını test eder.
Her soru için:
- Hangi method kullanıldı (internal/web_fallback)
- Kaynakların detayları (URL, başlık, yönetmelik adı)
- Cevap kalitesi
- Response süresi
"""

import requests
import json
import time
from datetime import datetime

# Railway URL
RAILWAY_URL = "https://legislationrag-production.up.railway.app"

# Test kategorileri ve sorular
TEST_CATEGORIES = {
    "🏗️ YAPI İŞLERİ (DB'de olmalı)": [
        {
            "question": "Yapı işlerinde korkuluk yüksekliği en az kaç cm olmalıdır?",
            "expected_source": "Yapı İşlerinde İSG Yönetmeliği",
            "expected_answer_contains": "110",
            "expected_method": "internal"
        },
        {
            "question": "Yapı işlerinde topuk levhası yüksekliği kaç santimetre olmalıdır?",
            "expected_source": "Yapı İşlerinde İSG Yönetmeliği",
            "expected_answer_contains": "15",
            "expected_method": "internal"
        },
        {
            "question": "İskele platformlarına güvenli ulaşım için ne kullanılır?",
            "expected_source": "Yapı İşlerinde İSG Yönetmeliği",
            "expected_answer_contains": "merdiven",
            "expected_method": "internal"
        },
        {
            "question": "Sütunlu çalışma platformlarında sesli ikaz sistemi ne zaman çalışır?",
            "expected_source": "Yapı İşlerinde İSG Yönetmeliği",
            "expected_answer_contains": "2,5",
            "expected_method": "internal"
        }
    ],
    
    "⚖️ 6331 KANUN (DB'de olmalı)": [
        {
            "question": "İş güvenliği uzmanı eğitim programı süresi kaç saattir?",
            "expected_source": "İş Güvenliği Uzmanları",
            "expected_answer_contains": "180",
            "expected_method": "internal"
        },
        {
            "question": "Risk değerlendirmesi kaç yılda bir yenilenmeli?",
            "expected_source": "Risk Değerlendirmesi",
            "expected_answer_contains": "yıl",
            "expected_method": "internal"
        },
        {
            "question": "İSG kurulu toplantısı ne sıklıkta yapılır?",
            "expected_source": "İSG Kurulları",
            "expected_answer_contains": "ay",
            "expected_method": "internal"
        },
        {
            "question": "Çok tehlikeli işyerlerinde iş güvenliği uzmanı çalışma süresi nedir?",
            "expected_source": "İş Güvenliği Uzmanları",
            "expected_answer_contains": "dakika",
            "expected_method": "internal"
        }
    ],
    
    "🔥 YANGIN GÜVENLİĞİ (DB'de olmalı)": [
        {
            "question": "Kaçış yolu koridor genişliği en az kaç cm olmalıdır?",
            "expected_source": "Binaların Yangından Korunması",
            "expected_answer_contains": "110",
            "expected_method": "internal"
        },
        {
            "question": "Yangın uyarı butonları yerden kaç cm yüksekliğe yerleştirilir?",
            "expected_source": "Binaların Yangından Korunması",
            "expected_answer_contains": "110",
            "expected_method": "internal"
        },
        {
            "question": "Yüksek binalarda kaçış merdiveni genişliği en az kaç cm?",
            "expected_source": "Binaların Yangından Korunması",
            "expected_answer_contains": "120",
            "expected_method": "internal"
        }
    ],
    
    "🧪 KİMYASAL MADDELER (DB'de olmalı)": [
        {
            "question": "Kimyasal maddelerle çalışmalarda mesleki maruziyet sınır değerleri nedir?",
            "expected_source": "Kimyasal Maddeler",
            "expected_answer_contains": "maruziyet",
            "expected_method": "internal"
        },
        {
            "question": "Kanserojen maddelere maruziyet nasıl kayıt altına alınır?",
            "expected_source": "Kanserojen",
            "expected_answer_contains": "kayıt",
            "expected_method": "internal"
        }
    ],
    
    "⛏️ MADEN İŞLERİ (DB'de olmalı)": [
        {
            "question": "Maden işyerlerinde havalandırma nasıl yapılmalıdır?",
            "expected_source": "Maden İşyerleri",
            "expected_answer_contains": "hava",
            "expected_method": "internal"
        },
        {
            "question": "Yeraltı maden işlerinde acil kaçış yolları nasıl olmalı?",
            "expected_source": "Maden İşyerleri",
            "expected_answer_contains": "kaçış",
            "expected_method": "internal"
        }
    ],
    
    "🛡️ KİŞİSEL KORUYUCU DONANIM (DB'de olmalı)": [
        {
            "question": "Kişisel koruyucu donanım seçiminde nelere dikkat edilmeli?",
            "expected_source": "Kişisel Koruyucu Donanım",
            "expected_answer_contains": "koruyucu",
            "expected_method": "internal"
        },
        {
            "question": "KKD'lerin CE işareti ne anlama gelir?",
            "expected_source": "Kişisel Koruyucu Donanım",
            "expected_answer_contains": "CE",
            "expected_method": "internal"
        }
    ],
    
    "🔌 ELEKTRİK GÜVENLİĞİ (DB'de olmalı)": [
        {
            "question": "Elektrik tesislerinde topraklama direnci kaç ohm olmalı?",
            "expected_source": "Elektrik Tesisleri",
            "expected_answer_contains": "ohm",
            "expected_method": "internal"
        },
        {
            "question": "Elektrik iç tesislerinde kaçak akım rölesi ne zaman zorunludur?",
            "expected_source": "Elektrik",
            "expected_answer_contains": "kaçak",
            "expected_method": "internal"
        }
    ],
    
    "🏭 İŞ EKİPMANLARI (DB'de olmalı)": [
        {
            "question": "Asansörlerin periyodik kontrolü ne sıklıkta yapılır?",
            "expected_source": "Asansör",
            "expected_answer_contains": "yıl",
            "expected_method": "internal"
        },
        {
            "question": "Basınçlı kapların periyodik muayenesi nasıl yapılır?",
            "expected_source": "Basınçlı",
            "expected_answer_contains": "muayene",
            "expected_method": "internal"
        },
        {
            "question": "Vinç ve kaldırma araçlarının kontrolü kim tarafından yapılır?",
            "expected_source": "İş Ekipmanları",
            "expected_answer_contains": "mühendis",
            "expected_method": "internal"
        }
    ],
    
    "🌐 GÜNCEL/WEB FALLBACK (DB'de olmayabilir)": [
        {
            "question": "2025 yılında iş sağlığı ve güvenliği mevzuatında yapılan son değişiklikler nelerdir?",
            "expected_source": "web",
            "expected_answer_contains": "2025",
            "expected_method": "web_fallback"
        },
        {
            "question": "ÇSGB'nin 2025 yılı iş kazası istatistikleri nedir?",
            "expected_source": "csgb.gov.tr",
            "expected_answer_contains": "kaza",
            "expected_method": "web_fallback"
        },
        {
            "question": "En son yayınlanan ISG tebliği hangisidir?",
            "expected_source": "web",
            "expected_answer_contains": "tebliğ",
            "expected_method": "web_fallback"
        }
    ],
    
    "🔍 EDGE CASES (Zor sorular)": [
        {
            "question": "Patlayıcı ortamlarda kullanılan ATEX sertifikalı ekipmanlar nelerdir?",
            "expected_source": "Patlayıcı Ortam",
            "expected_answer_contains": "patlayıcı",
            "expected_method": "internal"
        },
        {
            "question": "Asbest söküm işlemlerinde hangi önlemler alınmalı?",
            "expected_source": "Asbest",
            "expected_answer_contains": "asbest",
            "expected_method": "internal"
        },
        {
            "question": "Biyolojik etkenlere maruziyet risk grupları nelerdir?",
            "expected_source": "Biyolojik Etkenler",
            "expected_answer_contains": "grup",
            "expected_method": "internal"
        }
    ]
}

def format_source(source):
    """Kaynak bilgisini formatla"""
    if isinstance(source, dict):
        # Web source
        if 'link' in source:
            return f"🌐 {source.get('title', 'N/A')[:50]} | {source.get('link', 'N/A')[:60]}"
        # DB source
        elif 'source' in source:
            return f"📚 {source.get('title', source.get('document_title', 'N/A'))[:50]} | {source.get('source', 'N/A')[:40]}"
        elif 'document_title' in source:
            return f"📚 {source.get('document_title', 'N/A')[:50]} | Madde {source.get('madde_number', '?')}"
        else:
            return f"📄 {str(source)[:80]}"
    return str(source)[:80]

def test_question(question_data):
    """Tek bir soruyu test et"""
    question = question_data["question"]
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{RAILWAY_URL}/api/ask",
            json={"question": question},
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:100]}",
                "elapsed": elapsed
            }
        
        data = response.json()
        
        answer = data.get("answer", "")
        method = data.get("method", "unknown")
        sources = data.get("sources", [])
        confidence = data.get("confidence", "N/A")
        
        # Beklenen cevabı içeriyor mu?
        expected_in_answer = question_data["expected_answer_contains"].lower() in answer.lower()
        
        # Method doğru mu?
        expected_method = question_data["expected_method"]
        method_correct = (method == expected_method) or (expected_method == "internal" and method != "web_fallback")
        
        # Kaynak doğru mu?
        expected_source = question_data["expected_source"].lower()
        source_found = False
        for src in sources:
            src_str = str(src).lower()
            if expected_source in src_str:
                source_found = True
                break
        
        return {
            "success": True,
            "answer": answer,
            "method": method,
            "sources": sources,
            "confidence": confidence,
            "elapsed": elapsed,
            "expected_in_answer": expected_in_answer,
            "method_correct": method_correct,
            "source_found": source_found or method == "web_fallback"
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout (120s)",
            "elapsed": 120
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:100],
            "elapsed": time.time() - start_time
        }

def run_tests():
    """Tüm testleri çalıştır"""
    
    print("=" * 100)
    print("🧪 KAPSAMLI RAG SİSTEMİ TEST RAPORU")
    print(f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 URL: {RAILWAY_URL}")
    print("=" * 100)
    
    all_results = []
    category_stats = {}
    
    for category, questions in TEST_CATEGORIES.items():
        print(f"\n\n{'='*100}")
        print(f"📂 {category}")
        print("=" * 100)
        
        category_results = {
            "total": len(questions),
            "success": 0,
            "answer_correct": 0,
            "method_correct": 0,
            "source_correct": 0,
            "internal_count": 0,
            "web_count": 0
        }
        
        for i, q_data in enumerate(questions, 1):
            print(f"\n{'─'*100}")
            print(f"❓ Soru {i}/{len(questions)}: {q_data['question']}")
            print(f"   📌 Beklenen: method={q_data['expected_method']}, kaynak içerir='{q_data['expected_source']}', cevap içerir='{q_data['expected_answer_contains']}'")
            
            result = test_question(q_data)
            result["question"] = q_data["question"]
            result["category"] = category
            all_results.append(result)
            
            if result["success"]:
                category_results["success"] += 1
                
                # Method analizi
                method = result["method"]
                if method == "internal":
                    category_results["internal_count"] += 1
                    method_icon = "📚"
                else:
                    category_results["web_count"] += 1
                    method_icon = "🌐"
                
                # Sonuçları yazdır
                print(f"\n   ✅ BAŞARILI ({result['elapsed']:.1f}s)")
                print(f"   {method_icon} Method: {method}")
                print(f"   🎯 Confidence: {result.get('confidence', 'N/A')}")
                
                # Cevap önizleme
                answer = result["answer"][:300] + "..." if len(result["answer"]) > 300 else result["answer"]
                print(f"\n   💬 Cevap:\n   {answer}")
                
                # Kaynaklar
                print(f"\n   📚 Kaynaklar ({len(result['sources'])} adet):")
                for j, src in enumerate(result["sources"][:5], 1):
                    print(f"      {j}. {format_source(src)}")
                
                if len(result["sources"]) > 5:
                    print(f"      ... ve {len(result['sources']) - 5} kaynak daha")
                
                # Doğruluk kontrolleri
                checks = []
                if result["expected_in_answer"]:
                    checks.append("✅ Beklenen içerik cevabında var")
                    category_results["answer_correct"] += 1
                else:
                    checks.append(f"⚠️ '{q_data['expected_answer_contains']}' cevabında bulunamadı")
                
                if result["method_correct"]:
                    checks.append("✅ Method doğru")
                    category_results["method_correct"] += 1
                else:
                    checks.append(f"⚠️ Beklenen method: {q_data['expected_method']}, gerçek: {method}")
                
                if result["source_found"]:
                    checks.append("✅ Beklenen kaynak bulundu")
                    category_results["source_correct"] += 1
                else:
                    checks.append(f"⚠️ '{q_data['expected_source']}' kaynaklarda bulunamadı")
                
                print(f"\n   🔍 Doğruluk Kontrolleri:")
                for check in checks:
                    print(f"      {check}")
                
            else:
                print(f"\n   ❌ BAŞARISIZ ({result['elapsed']:.1f}s)")
                print(f"   Hata: {result['error']}")
        
        category_stats[category] = category_results
        
        # Kategori özeti
        print(f"\n{'─'*100}")
        print(f"📊 Kategori Özeti: {category_results['success']}/{category_results['total']} başarılı")
        print(f"   📚 Internal: {category_results['internal_count']} | 🌐 Web: {category_results['web_count']}")
        print(f"   ✅ Cevap doğru: {category_results['answer_correct']} | Method doğru: {category_results['method_correct']} | Kaynak doğru: {category_results['source_correct']}")
    
    # GENEL ÖZET
    print("\n\n" + "=" * 100)
    print("📊 GENEL TEST RAPORU")
    print("=" * 100)
    
    total_questions = sum(c["total"] for c in category_stats.values())
    total_success = sum(c["success"] for c in category_stats.values())
    total_internal = sum(c["internal_count"] for c in category_stats.values())
    total_web = sum(c["web_count"] for c in category_stats.values())
    total_answer_correct = sum(c["answer_correct"] for c in category_stats.values())
    total_method_correct = sum(c["method_correct"] for c in category_stats.values())
    total_source_correct = sum(c["source_correct"] for c in category_stats.values())
    
    print(f"""
┌{'─'*98}┐
│ {'METRIK':<40} │ {'DEĞER':>20} │ {'YÜZDE':>15} │ {'DURUM':>15} │
├{'─'*98}┤
│ {'Toplam Soru':<40} │ {total_questions:>20} │ {'':>15} │ {'':>15} │
│ {'Başarılı Yanıt':<40} │ {total_success:>20} │ {100*total_success/total_questions:>14.1f}% │ {'✅' if total_success == total_questions else '⚠️':>15} │
│ {'Internal (MongoDB)':<40} │ {total_internal:>20} │ {100*total_internal/total_success if total_success > 0 else 0:>14.1f}% │ {'📚':>15} │
│ {'Web Fallback (Serper)':<40} │ {total_web:>20} │ {100*total_web/total_success if total_success > 0 else 0:>14.1f}% │ {'🌐':>15} │
│ {'Cevap İçerik Doğruluğu':<40} │ {total_answer_correct:>20} │ {100*total_answer_correct/total_success if total_success > 0 else 0:>14.1f}% │ {'✅' if total_answer_correct/total_success > 0.8 else '⚠️':>15} │
│ {'Method Doğruluğu':<40} │ {total_method_correct:>20} │ {100*total_method_correct/total_success if total_success > 0 else 0:>14.1f}% │ {'✅' if total_method_correct/total_success > 0.8 else '⚠️':>15} │
│ {'Kaynak Doğruluğu':<40} │ {total_source_correct:>20} │ {100*total_source_correct/total_success if total_success > 0 else 0:>14.1f}% │ {'✅' if total_source_correct/total_success > 0.8 else '⚠️':>15} │
└{'─'*98}┘
""")
    
    # Kategori bazlı özet
    print("\n📂 KATEGORİ BAZLI SONUÇLAR:")
    print("─" * 100)
    
    for category, stats in category_stats.items():
        success_rate = 100 * stats["success"] / stats["total"] if stats["total"] > 0 else 0
        status = "✅" if success_rate == 100 else "⚠️" if success_rate >= 80 else "❌"
        
        internal_pct = 100 * stats["internal_count"] / stats["success"] if stats["success"] > 0 else 0
        web_pct = 100 * stats["web_count"] / stats["success"] if stats["success"] > 0 else 0
        
        print(f"{status} {category}")
        print(f"   Başarı: {stats['success']}/{stats['total']} ({success_rate:.0f}%) | 📚 Internal: {internal_pct:.0f}% | 🌐 Web: {web_pct:.0f}%")
    
    # Kaynak analizi
    print("\n\n📚 KAYNAK ANALİZİ:")
    print("─" * 100)
    
    source_stats = {"internal": {}, "web": {}}
    
    for result in all_results:
        if result["success"]:
            method = result["method"]
            for src in result.get("sources", []):
                if isinstance(src, dict):
                    if method == "internal" or method == "hybrid":
                        key = src.get("document_title", src.get("source", str(src)))[:50]
                        source_stats["internal"][key] = source_stats["internal"].get(key, 0) + 1
                    else:
                        # Web source - domain'i çıkar
                        link = src.get("link", "")
                        if link:
                            domain = link.split("/")[2] if len(link.split("/")) > 2 else link
                            source_stats["web"][domain] = source_stats["web"].get(domain, 0) + 1
    
    print("\n📚 En Çok Kullanılan MongoDB Kaynakları:")
    for src, count in sorted(source_stats["internal"].items(), key=lambda x: -x[1])[:10]:
        print(f"   [{count:2d}x] {src}")
    
    print("\n🌐 En Çok Kullanılan Web Kaynakları:")
    for src, count in sorted(source_stats["web"].items(), key=lambda x: -x[1])[:10]:
        print(f"   [{count:2d}x] {src}")
    
    # Süre analizi
    print("\n\n⏱️ PERFORMANS ANALİZİ:")
    print("─" * 100)
    
    times = [r["elapsed"] for r in all_results if r["success"]]
    if times:
        print(f"   Ortalama yanıt süresi: {sum(times)/len(times):.2f}s")
        print(f"   En hızlı: {min(times):.2f}s")
        print(f"   En yavaş: {max(times):.2f}s")
        
        internal_times = [r["elapsed"] for r in all_results if r["success"] and r["method"] == "internal"]
        web_times = [r["elapsed"] for r in all_results if r["success"] and r["method"] != "internal"]
        
        if internal_times:
            print(f"   📚 Internal ortalama: {sum(internal_times)/len(internal_times):.2f}s")
        if web_times:
            print(f"   🌐 Web fallback ortalama: {sum(web_times)/len(web_times):.2f}s")
    
    # JSON export
    print("\n\n💾 Test sonuçları 'test_results.json' dosyasına kaydedildi.")
    
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "url": RAILWAY_URL,
            "summary": {
                "total": total_questions,
                "success": total_success,
                "internal": total_internal,
                "web": total_web,
                "answer_correct": total_answer_correct,
                "method_correct": total_method_correct,
                "source_correct": total_source_correct
            },
            "categories": category_stats,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 100)
    print(f"🏁 TEST TAMAMLANDI: {total_success}/{total_questions} başarılı ({100*total_success/total_questions:.1f}%)")
    print("=" * 100)
    
    return all_results

if __name__ == "__main__":
    run_tests()
