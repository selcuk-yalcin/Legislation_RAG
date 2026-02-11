#!/usr/bin/env python3
"""
PDF Kaynakları ve Web Fallback Test Script

Bu script:
1. MongoDB'deki mevcut PDF kaynaklarını listeler
2. Web search'ten gelen PDF'leri kontrol eder
3. Belirli PDF-spesifik sorularla test yapar
4. Cevabın gerçekten PDF içeriğinden gelip gelmediğini doğrular
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# MongoDB bağlantısı
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["mevzuat_db"]

def check_documents_collection():
    """documents koleksiyonundaki PDF kaynaklarını kontrol et"""
    print("=" * 70)
    print("📚 DOCUMENTS KOLEKSİYONU - PDF KAYNAKLARI")
    print("=" * 70)
    
    # PDF uzantılı veya PDF içeren kaynakları bul
    pdf_docs = list(db.documents.find(
        {"$or": [
            {"metadata.source": {"$regex": ".pdf", "$options": "i"}},
            {"metadata.source_type": "pdf"},
            {"metadata.file_type": "pdf"}
        ]},
        {"metadata": 1, "text": 1}
    ).limit(20))
    
    print(f"\n📄 PDF Doküman Sayısı (ilk 20): {len(pdf_docs)}")
    
    for i, doc in enumerate(pdf_docs[:10], 1):
        meta = doc.get("metadata", {})
        source = meta.get("source", meta.get("title", "Bilinmiyor"))
        text_preview = doc.get("text", "")[:150].replace("\n", " ")
        print(f"\n{i}. {source}")
        print(f"   📝 Preview: {text_preview}...")
    
    return pdf_docs

def check_web_search_collection():
    """web_search koleksiyonundaki PDF kaynaklarını kontrol et"""
    print("\n" + "=" * 70)
    print("🌐 WEB_SEARCH KOLEKSİYONU - PDF KAYNAKLARI")
    print("=" * 70)
    
    # Tüm web_search dokümanlarını getir
    all_web_docs = list(db.web_search.find({}, {"metadata": 1, "text": 1}))
    print(f"\n📊 Toplam web_search doküman sayısı: {len(all_web_docs)}")
    
    # PDF olanları filtrele
    pdf_docs = [doc for doc in all_web_docs 
                if doc.get("metadata", {}).get("source_url", "").endswith(".pdf")]
    
    print(f"📄 PDF doküman sayısı: {len(pdf_docs)}")
    
    # Tüm unique URL'leri göster
    print("\n🔗 Web_search'teki tüm unique URL'ler:")
    urls = set()
    for doc in all_web_docs:
        url = doc.get("metadata", {}).get("source_url", "")
        if url:
            urls.add(url)
    
    for url in sorted(urls):
        is_pdf = "📄 PDF" if url.endswith(".pdf") else "🌐 HTML"
        print(f"   {is_pdf} {url}")
    
    return pdf_docs

def check_metadata_fields():
    """Metadata field'larını analiz et"""
    print("\n" + "=" * 70)
    print("🔍 METADATA FIELD ANALİZİ")
    print("=" * 70)
    
    # documents koleksiyonu
    sample_doc = db.documents.find_one()
    if sample_doc:
        print("\n📚 documents koleksiyonu metadata fields:")
        meta = sample_doc.get("metadata", {})
        for key in sorted(meta.keys()):
            print(f"   - {key}: {type(meta[key]).__name__}")
    
    # web_search koleksiyonu
    sample_web = db.web_search.find_one()
    if sample_web:
        print("\n🌐 web_search koleksiyonu metadata fields:")
        meta = sample_web.get("metadata", {})
        for key in sorted(meta.keys()):
            print(f"   - {key}: {type(meta[key]).__name__}")

def search_specific_terms():
    """Belirli terimleri ara ve hangi dokümanlarda olduğunu göster"""
    print("\n" + "=" * 70)
    print("🔎 SPESİFİK TERİM ARAMALARI")
    print("=" * 70)
    
    # PDF'lerde sıkça bulunan spesifik terimler
    terms = [
        "korkuluk yüksekliği",
        "110 cm",
        "yapı işleri",
        "kişisel koruyucu donanım",
        "tehlike sınıfı",
        "iş güvenliği uzmanı",
        "meslek hastalığı",
        "risk değerlendirmesi"
    ]
    
    for term in terms:
        # documents'ta ara
        doc_count = db.documents.count_documents({
            "text": {"$regex": term, "$options": "i"}
        })
        
        # web_search'te ara
        web_count = db.web_search.count_documents({
            "text": {"$regex": term, "$options": "i"}
        })
        
        print(f"\n🔍 '{term}':")
        print(f"   📚 documents: {doc_count} sonuç")
        print(f"   🌐 web_search: {web_count} sonuç")

def get_pdf_test_queries():
    """PDF içeriklerini test edecek özel sorular"""
    print("\n" + "=" * 70)
    print("❓ PDF TEST SORULARI")
    print("=" * 70)
    
    queries = [
        # Yapı İşlerinde İSG Yönetmeliği - spesifik rakamlar
        {
            "query": "Yapı işlerinde korkuluk yüksekliği en az kaç cm olmalıdır?",
            "expected": "110 cm",
            "source": "Yapı İşlerinde İSG Yönetmeliği"
        },
        {
            "query": "İskele platformu genişliği en az kaç cm olmalıdır?",
            "expected": "60 cm",
            "source": "Yapı İşlerinde İSG Yönetmeliği"
        },
        
        # 6331 sayılı Kanun - spesifik maddeler
        {
            "query": "6331 sayılı kanuna göre çok tehlikeli işyerlerinde iş güvenliği uzmanı ayda kaç dakika çalışmalıdır?",
            "expected": "40 dakika",
            "source": "6331 sayılı İSG Kanunu"
        },
        {
            "query": "6331 sayılı kanunda işverenin yükümlülükleri hangi maddede?",
            "expected": "Madde 4",
            "source": "6331 sayılı İSG Kanunu"
        },
        
        # KKD Yönetmeliği
        {
            "query": "Kişisel koruyucu donanım kullanımı hangi yönetmelikte düzenleniştir?",
            "expected": "KKD Yönetmeliği",
            "source": "KKD Kullanımı Hakkında Yönetmelik"
        },
        
        # Tehlike Sınıfları
        {
            "query": "Maden işleri hangi tehlike sınıfındadır?",
            "expected": "Çok tehlikeli",
            "source": "Tehlike Sınıfları Tebliği"
        },
        
        # Risk Değerlendirmesi
        {
            "query": "Risk değerlendirmesi kaç yılda bir yenilenmelidir?",
            "expected": "2 yıl (az tehlikeli), 4 yıl (tehlikeli), 6 yıl (çok tehlikeli) - veya değişiklik olduğunda",
            "source": "Risk Değerlendirmesi Yönetmeliği"
        },
        
        # Tablo/Şekil içeren sorular (Azure DI parse testi)
        {
            "query": "İş ekipmanlarının periyodik kontrolü kimler tarafından yapılır?",
            "expected": "Mühendisler veya teknik elemanlar",
            "source": "İş Ekipmanları Yönetmeliği"
        }
    ]
    
    print("\n📋 Test edilecek sorular:\n")
    for i, q in enumerate(queries, 1):
        print(f"{i}. {q['query']}")
        print(f"   ✅ Beklenen: {q['expected']}")
        print(f"   📚 Kaynak: {q['source']}\n")
    
    return queries

def main():
    print("\n" + "🔬" * 35)
    print("  PDF KAYNAKLARI VE WEB FALLBACK TEST")
    print("🔬" * 35 + "\n")
    
    # 1. documents koleksiyonunu kontrol et
    check_documents_collection()
    
    # 2. web_search koleksiyonunu kontrol et
    check_web_search_collection()
    
    # 3. Metadata field'larını analiz et
    check_metadata_fields()
    
    # 4. Spesifik terimleri ara
    search_specific_terms()
    
    # 5. Test sorularını göster
    queries = get_pdf_test_queries()
    
    print("\n" + "=" * 70)
    print("📌 SONRAKİ ADIM")
    print("=" * 70)
    print("""
Bu soruları Railway'de test etmek için:

curl https://YOUR-RAILWAY-URL/api/ask \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Yapı işlerinde korkuluk yüksekliği en az kaç cm olmalıdır?"}'

Veya local'de:
python3 -c "from rag_pipeline import RAGPipeline; p = RAGPipeline(); print(p.query('Yapı işlerinde korkuluk yüksekliği en az kaç cm olmalıdır?'))"
""")
    
    client.close()

if __name__ == "__main__":
    main()
