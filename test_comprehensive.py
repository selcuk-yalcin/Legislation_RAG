"""
Comprehensive RAG System Test - 30 Questions
Tests Railway deployment with diverse questions
"""

import requests
import json
import time
from datetime import datetime

# Railway API URL
API_URL = "https://legislationrag-production.up.railway.app/query"

# 30 Test Questions covering different aspects
TEST_QUESTIONS = [
    # İş Güvenliği Uzmanı
    "İş güvenliği uzmanlarının çalışma süreleri nedir?",
    "İş güvenliği uzmanı kimler olabilir?",
    "İş güvenliği uzmanının görevleri nelerdir?",
    
    # İşyeri Hekimi
    "İşyeri hekimi görevlendirmesi nasıl yapılır?",
    "İşyeri hekiminin çalışma süreleri ne kadardır?",
    "İşyeri hekiminin sorumlulukları nelerdir?",
    
    # Risk Değerlendirmesi
    "Risk değerlendirmesi nasıl yapılır?",
    "Risk değerlendirmesi kimler tarafından yapılır?",
    "Risk değerlendirmesinde hangi adımlar izlenir?",
    
    # İşveren Yükümlülükleri
    "İşverenin iş sağlığı ve güvenliği konusundaki görevleri nelerdir?",
    "İşveren hangi durumlarda acil eylem planı hazırlamalıdır?",
    "İşverenin eğitim yükümlülükleri nelerdir?",
    
    # Çalışan Hakları
    "Çalışanların iş sağlığı ve güvenliği konusundaki hakları nelerdir?",
    "Çalışanlar hangi durumlarda çalışmayı durdurabilir?",
    "Çalışan temsilcisinin yetkileri nelerdir?",
    
    # Kişisel Koruyucu Donanım
    "Kişisel koruyucu donanım (KKD) kullanımı zorunlu mudur?",
    "KKD maliyeti kime aittir?",
    "KKD seçiminde nelere dikkat edilmelidir?",
    
    # İş Kazası ve Meslek Hastalığı
    "İş kazası bildirimi nasıl yapılır?",
    "Meslek hastalığı nedir?",
    "İş kazasında işverenin sorumlulukları nelerdir?",
    
    # Sağlık Gözetimi
    "Sağlık muayeneleri hangi sıklıkla yapılmalıdır?",
    "Hangi çalışanlar sağlık muayenesine tabi tutulmalıdır?",
    "Sağlık raporlarının gizliliği nasıl sağlanır?",
    
    # Tehlikeli Maddeler
    "Tehlikeli madde kullanımında alınması gereken önlemler nelerdir?",
    "Kimyasal maddelerin etiketlenmesi nasıl olmalıdır?",
    "Biyolojik etkenlerden korunma yöntemleri nelerdir?",
    
    # Yangın ve Acil Durumlar
    "Yangın söndürme ekipmanları nasıl seçilmelidir?",
    "Acil durum planı nasıl hazırlanır?",
    "Tahliye tatbikatı ne sıklıkla yapılmalıdır?"
]

def test_question(question, question_num, total):
    """Test a single question and return results"""
    print(f"\n{'='*80}")
    print(f"Soru {question_num}/{total}: {question}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            json={"question": question},
            timeout=60
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', 'No answer')
            sources = data.get('sources', [])
            
            # Extract first 200 chars of answer
            answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
            
            print(f"✅ BAŞARILI ({elapsed_time:.2f}s)")
            print(f"📝 Cevap: {answer_preview}")
            print(f"📚 Kaynak Sayısı: {len(sources) if sources else 'Bilinmiyor'}")
            
            return {
                'question': question,
                'status': 'success',
                'response_time': elapsed_time,
                'answer_length': len(answer),
                'sources_count': len(sources) if sources else 0
            }
        else:
            print(f"❌ HATA: HTTP {response.status_code}")
            return {
                'question': question,
                'status': 'error',
                'error': f"HTTP {response.status_code}",
                'response_time': elapsed_time
            }
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ EXCEPTION: {str(e)}")
        return {
            'question': question,
            'status': 'exception',
            'error': str(e),
            'response_time': elapsed_time
        }

def main():
    """Run comprehensive test"""
    print("\n" + "="*80)
    print("🚀 KAPSAMLI RAG SİSTEM TESTİ")
    print("="*80)
    print(f"📍 API URL: {API_URL}")
    print(f"📊 Test Soru Sayısı: {len(TEST_QUESTIONS)}")
    print(f"🕐 Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    results = []
    
    for i, question in enumerate(TEST_QUESTIONS, 1):
        result = test_question(question, i, len(TEST_QUESTIONS))
        results.append(result)
        
        # Small delay between requests
        if i < len(TEST_QUESTIONS):
            time.sleep(2)
    
    # Summary Report
    print("\n" + "="*80)
    print("📊 TEST ÖZET RAPORU")
    print("="*80)
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']
    
    print(f"\n✅ Başarılı: {len(successful)}/{len(results)}")
    print(f"❌ Başarısız: {len(failed)}/{len(results)}")
    
    if successful:
        avg_time = sum(r['response_time'] for r in successful) / len(successful)
        avg_length = sum(r['answer_length'] for r in successful) / len(successful)
        avg_sources = sum(r.get('sources_count', 0) for r in successful) / len(successful)
        
        print(f"\n⏱️  Ortalama Yanıt Süresi: {avg_time:.2f}s")
        print(f"📏 Ortalama Cevap Uzunluğu: {avg_length:.0f} karakter")
        print(f"📚 Ortalama Kaynak Sayısı: {avg_sources:.1f}")
    
    if failed:
        print(f"\n❌ Başarısız Sorular:")
        for r in failed:
            print(f"   - {r['question'][:50]}... ({r['status']}: {r.get('error', 'Unknown')})")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'total_questions': len(TEST_QUESTIONS),
            'successful': len(successful),
            'failed': len(failed),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Sonuçlar kaydedildi: {filename}")
    print("="*80)

if __name__ == "__main__":
    main()
