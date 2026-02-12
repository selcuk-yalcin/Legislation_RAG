# 📚 KILAVUZLAR UPLOAD SİSTEMİ - HAZIR!

## ✅ NE YAPILDI?

### 1. Yeni MongoDB Collection: `guides`
- Kılavuzlar artık mevzuatlardan ayrı tutulacak
- Daha organize ve temiz veri yapısı
- Collection: `mevzuat_db.guides`

### 2. Azure Document Intelligence Integration
- **75 PDF kılavuz** Azure DI ile parse edilecek
- **Tablolar korunacak** (PyPDFLoader'dan farklı olarak)
- **Markdown format** (heading structure preserved)
- **Şekil/görsel tespiti** aktif

### 3. Heading-Based Semantic Chunking
- MADDE bazlı değil, heading bazlı split (### headings)
- Her chunk 1500 char (optimal for embeddings)
- 200 char overlap (context preservation)
- Semantic bütünlük korunuyor

### 4. Voyage AI Embeddings
- Model: `voyage-law-2` (1024-dim)
- Türk hukuku için optimize
- Batch processing (hızlı)

### 5. Hybrid Search Update
- MongoDB vector store artık 3 collection arıyor:
  1. `documents` (kanun/yönetmelik)
  2. `web_search` (web fallback results)
  3. `guides` (kılavuzlar) ← YENİ!

---

## 📊 UPLOAD İSTATİSTİKLERİ (TAHMİNİ)

```
📂 Toplam Kılavuz: 75 PDF
📄 Ortalama Boyut: ~5 MB/PDF
⏱️  Ortalama İşlem: ~30-45 saniye/PDF

Beklenen Süreler:
├─ Azure DI parsing: ~15-20s/PDF
├─ Chunking: ~2-3s/PDF
├─ Voyage embedding: ~5-10s/PDF
└─ MongoDB upload: ~2-3s/PDF

🕐 Toplam Süre: ~40-60 dakika (75 PDF × ~40s)

💰 Maliyet Tahmini:
├─ Azure DI: 75 PDF × ~5 MB = 375 MB
│   └─ Cost: ~$2.80 ($1.50/1000 pages)
│
├─ Voyage AI: 75 PDF × ~50 chunks = 3,750 chunks
│   └─ Cost: ~$0.40 ($0.10/1M tokens)
│
└─ TOPLAM: ~$3.20
```

---

## 🚀 NASIL ÇALIŞTIRILIR?

### Manuel Upload (Önerilen)

```bash
cd /Users/selcuk/Desktop/admin_pan/Legislation_RAG
python upload_klavuzlar_with_azure.py
```

**Adımlar:**
1. Script çalıştır
2. "Proceed with upload? (y/n):" → `y` yaz
3. 75 PDF tek tek işlenecek (progress bar var)
4. Sonunda MongoDB Atlas'ta vector index oluşturma talimatı verilecek
5. Atlas UI'da index oluştur (tek seferlik)

### Vector Index Oluşturma (MongoDB Atlas UI)

Script bitince şu adımları izle:

1. https://cloud.mongodb.com → Login
2. Database → Browse Collections → `guides`
3. "Search Indexes" tab → "Create Search Index"
4. "JSON Editor" seç
5. Şu konfigürasyonu yapıştır:

```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "dimensions": 1024,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}
```

6. Name: `guides_vector_index`
7. Create!

---

## 🧪 TEST

Upload bittikten sonra test et:

```python
from mongodb_vector_store import get_mongodb_vectorstore

# Initialize
store = get_mongodb_vectorstore()

# Stats check
stats = store.get_collection_stats()
print(f"Documents: {stats['documents']['count']}")
print(f"Web Search: {stats['web_search']['count']}")
print(f"Guides: {stats['guides']['count']}")  # ← Burası >0 olmalı
print(f"TOTAL: {stats['total_documents']}")

# Search test
results = store.similarity_search(
    query="Risk değerlendirmesi nasıl yapılır?",
    k=10,
    search_guides=True  # ← Guide'ları da ara
)

# Check sources
for doc in results[:5]:
    collection_type = doc.metadata.get('collection_type', 'document')
    title = doc.metadata.get('guide_title') or doc.metadata.get('document_title')
    print(f"[{collection_type}] {title}")
```

---

## 📋 ÖRNEK KULLANIM (RAG Pipeline'da)

Guides artık otomatik olarak aranacak:

```python
# hybrid_pipeline.py içinde
result = self.rag.query(
    query="KKD rehberi nedir?",
    top_k=15
)

# Sonuçlar hem mevzuat hem kılavuzlardan gelecek!
# metadata.collection_type = "guide" | "document" | "web_search"
```

---

## ⚠️  ÖNEMLİ NOTLAR

1. **İlk Upload Uzun Sürer**
   - 75 PDF × 40s = ~50 dakika
   - Script background'da çalışabilir
   - Skip existing aktif (ikinci çalıştırmada hızlı)

2. **Azure DI Limitleri**
   - Max 15 req/min (Free tier)
   - Script otomatik rate limiting yapıyor
   - Premium tier: daha hızlı

3. **Voyage AI Limitleri**
   - Batch processing kullanılıyor
   - Rate limit nadiren sorun olur

4. **MongoDB Atlas**
   - Free tier: 512MB limit
   - Guides: ~50-100 MB (tahmini)
   - Documents: ~200-300 MB
   - Web search: ~50-100 MB
   - **TOPLAM: ~400-500 MB** (free tier yeterli!)

---

## 🎯 BEKLENENHasıl

Upload bittikten sonra:

```
MongoDB Collections:
├─ documents:   ~15,000 chunks (kanun/yönetmelik)
├─ web_search:  ~4,000 chunks (web fallback)
└─ guides:      ~3,750 chunks (kılavuzlar) ← YENİ!

Toplam: ~22,750 searchable chunks!
```

**RAG Query Örneği:**

```
Soru: "İnşaatta iskele güvenliği nasıl sağlanır?"

Sonuçlar:
1. [guide] Cephe İskelelerinde Güvenli Çalışma Rehberi
2. [document] İnşaat İşlerinde İSG Yönetmeliği
3. [guide] İnşaat İşlerinde Risk Değerlendirmesi Rehberi
4. [web_search] ÇSGB - İskele Güvenliği Duyurusu
5. [document] Geçici ve Hareketli İş Ekipmanları Yönetmeliği
```

→ **Daha zengin ve pratik cevaplar!**

---

## ✅ HAZIR!

Tüm sistem hazır. Sadece şunu çalıştır:

```bash
python upload_klavuzlar_with_azure.py
```

Ve bekle! ☕
