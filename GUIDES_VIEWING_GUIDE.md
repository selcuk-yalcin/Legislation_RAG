# 📊 KILAVUZLARI GÖRÜNTÜLEME REHBERİ

## 🎯 Kılavuzları 3 Formatta Görebilirsiniz:

### 1️⃣ **MongoDB'de (Canlı Database)**
```python
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
guides = db["guides"]

# İstatistikler
print(f"Toplam chunk: {guides.count_documents({})}")

# İlk 5 chunk'ı gör
for doc in guides.find().limit(5):
    print(f"\nTitle: {doc['metadata']['guide_title']}")
    print(f"Chunk {doc['metadata']['chunk_index']}")
    print(f"Content: {doc['content'][:200]}...")
```

### 2️⃣ **JSON Formatında (Yapılandırılmış Data)**

Upload sonrası otomatik export veya manuel:
```bash
python export_guides.py
```

**Çıktı:**
```
guides_output/
├── guides_summary.json          ← Genel özet
├── sample_chunks.json           ← 5 örnek chunk
├── json/
│   ├── acil-durum-planı.json    ← Her kılavuz ayrı dosya
│   ├── iskele-güvenliği.json
│   └── ...
```

**JSON İçeriği:**
```json
{
  "guide_title": "Acil Durum Planı Hazırlama Rehberi",
  "source_file": "acil-durum-planı-hazırlama-rehberi.pdf",
  "total_chunks": 45,
  "exported_at": "2026-02-12T15:30:00",
  "chunks": [
    {
      "chunk_index": 0,
      "content": "# Acil Durum Planı\n\n## Giriş\n...",
      "metadata": {
        "guide_title": "...",
        "source_file": "...",
        "chunk_type": "markdown",
        "collection_type": "guide"
      }
    }
  ]
}
```

### 3️⃣ **Markdown Formatında (İnsan Okunabilir)**

Export script ile:
```bash
python export_guides.py
# Option 3: Markdown only
```

**Çıktı:**
```
guides_output/markdown/
├── acil-durum-planı.md
├── iskele-güvenliği.md
└── ...
```

**Markdown İçeriği:**
```markdown
# Acil Durum Planı Hazırlama Rehberi

**Source File:** `acil-durum-planı-hazırlama-rehberi.pdf`  
**Total Chunks:** 45  
**Exported:** 2026-02-12 15:30:00

---

## Chunk 1/45

# Acil Durum Planı

## Giriş

Acil durum planları işyerlerinde olası tehlikelere karşı 
hazırlıklı olmak için hazırlanır...

---

## Chunk 2/45

## Risk Analizi

| Risk Türü | Olasılık | Etki |
|-----------|----------|------|
| Yangın    | Yüksek   | Kritik |
| Deprem    | Orta     | Yüksek |

---
```

---

## 🚀 KULLANIM ÖRNEKLERİ

### Senaryo 1: Upload Sonrası İnceleme

```bash
# 1. Upload yap
python upload_klavuzlar_with_azure.py
# "Export now? (y/n):" → y yaz

# 2. Dosyalar otomatik oluşur:
# guides_output/ klasörü oluşur
```

### Senaryo 2: Sadece Export (MongoDB'de Varsa)

```bash
# Kılavuzlar zaten MongoDB'de, sadece export et
python export_guides.py

# Seçenekler:
# 1. Full export (JSON + MD + Summary) ← ÖNERİLEN
# 2. JSON only
# 3. Markdown only
# 4. Summary only
# 5. Sample chunks only
```

### Senaryo 3: Programatik Erişim

```python
# Python script içinde kullan
from export_guides import GuidesExporter

exporter = GuidesExporter()

# Sadece özet
exporter.export_summary()

# Hepsi birden
exporter.run_full_export(include_embeddings=False)
```

---

## 📋 EXPORT FORMAT DETAYLARI

### JSON Format (Structured)

**Avantajlar:**
- ✅ Programatik erişim kolay
- ✅ Metadata tam olarak korunuyor
- ✅ Chunk index'ler net
- ✅ Embedding'ler opsiyonel olarak dahil

**Kullanım Alanları:**
- Veri analizi
- Backup
- Migration
- API integration

### Markdown Format (Human-Readable)

**Avantajlar:**
- ✅ Okumak çok kolay
- ✅ GitHub/GitLab'da preview
- ✅ Tablo formatları korunuyor
- ✅ Heading yapısı net görünüyor

**Kullanım Alanları:**
- Manuel inceleme
- Dökümentasyon
- Review
- Kalite kontrolü

### Summary JSON (Overview)

**İçerik:**
```json
{
  "export_date": "2026-02-12T15:30:00",
  "total_guides": 75,
  "total_chunks": 3750,
  "total_characters": 5625000,
  "guides": [
    {
      "title": "Acil Durum Planı",
      "source_file": "acil-durum-planı.pdf",
      "chunks": 45,
      "characters": 67500,
      "processed_at": "2026-02-12T14:00:00"
    }
  ]
}
```

**Kullanım:**
- Hızlı overview
- İstatistik raporları
- Progress tracking

---

## 🔍 ÖRNEK ÇIKTILAR

### guides_summary.json
```json
{
  "total_guides": 75,
  "total_chunks": 3750,
  "total_characters": 5625000,
  "guides": [
    {"title": "Acil Durum Planı", "chunks": 45},
    {"title": "İskele Güvenliği", "chunks": 52},
    ...
  ]
}
```

### sample_chunks.json
```json
[
  {
    "chunk_index": 0,
    "content": "# Acil Durum Planı\n\n...",
    "metadata": {
      "guide_title": "Acil Durum Planı",
      "source_file": "acil-durum.pdf",
      "collection_type": "guide",
      "origin": "web_search"
    },
    "embedding": "[1024 dimensions - truncated]"
  }
]
```

### İndividual JSON (acil-durum-planı.json)
```json
{
  "guide_title": "Acil Durum Planı Hazırlama Rehberi",
  "source_file": "acil-durum-planı-hazırlama-rehberi.pdf",
  "total_chunks": 45,
  "chunks": [
    {
      "chunk_index": 0,
      "content": "# Acil Durum Planı...",
      "metadata": {...}
    },
    ...
  ]
}
```

---

## 💡 TAVSİYELER

### 1. İlk Upload Sonrası
```bash
# Full export yap (her şeyi görmek için)
python export_guides.py
# Option: 1 (Full export)
# Embeddings: n (dosya boyutu büyür)
```

### 2. Kalite Kontrolü
```bash
# Markdown export yap → VSCode'da aç → oku
python export_guides.py
# Option: 3 (Markdown only)

# Tablolar doğru parse edilmiş mi?
# Heading'ler doğru mu?
# İçerik kaybolmuş mu?
```

### 3. Backup
```bash
# JSON export (embeddings ile)
python export_guides.py
# Option: 2 (JSON only)
# Embeddings: y (tam backup)

# guides_output/json/ klasörünü zip'le
zip -r guides_backup_2026-02-12.zip guides_output/json/
```

### 4. Hızlı Preview
```bash
# Sadece summary ve samples
python export_guides.py
# Option: 4 (Summary only)

# Sonra sample'lara bak
cat guides_output/sample_chunks.json | jq '.[0]'
```

---

## 📂 DOSYA YAPISI (Upload + Export Sonrası)

```
Legislation_RAG/
├── data/
│   └── KLAVUZLAR/              ← Original PDFs (75 adet)
│
├── guides_output/              ← Export çıktıları
│   ├── guides_summary.json     (15 KB)
│   ├── sample_chunks.json      (50 KB)
│   ├── json/                   (75 dosya, ~30 MB)
│   │   ├── acil-durum-planı.json
│   │   ├── iskele-güvenliği.json
│   │   └── ...
│   └── markdown/               (75 dosya, ~25 MB)
│       ├── acil-durum-planı.md
│       ├── iskele-güvenliği.md
│       └── ...
│
└── MongoDB Atlas:              ← Live database
    └── mevzuat_db.guides       (3750 chunks, ~100 MB)
```

---

## ✅ ÖZET

| Format | Boyut | Kullanım | Avantaj |
|--------|-------|----------|---------|
| **MongoDB** | ~100 MB | RAG search | ✅ Vector search, ⚡ Hızlı |
| **JSON** | ~30 MB | Programatik | ✅ Structured, 🔧 Flexible |
| **Markdown** | ~25 MB | İnsan okuma | ✅ Readable, 📝 Clean |
| **Summary** | ~15 KB | Overview | ✅ Fast, 📊 Stats |

**Hepsini kullanabilirsin!** 🎉
