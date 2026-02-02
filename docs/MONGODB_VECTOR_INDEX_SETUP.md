# MongoDB Atlas Vector Search Index Kurulum Rehberi

## Özet
MongoDB Atlas'ta vector search kullanabilmek için **Search Index** oluşturmanız gerekiyor. Bu işlem MongoDB Atlas UI üzerinden yapılır.

---

## Adım 1: MongoDB Atlas'a Giriş Yapın
1. https://cloud.mongodb.com adresine gidin
2. Hesabınızla giriş yapın
3. **mevzuat_db** database'ini bulun

---

## Adım 2: Search Index Oluşturun
1. **Database Deployments** → Cluster'ınızı seçin
2. **Browse Collections** butonuna tıklayın
3. `mevzuat_db` → `documents` koleksiyonunu seçin
4. Üst menüden **"Search Indexes"** (🔍 Arama simgesi) sekmesine tıklayın
5. **"Create Search Index"** butonuna tıklayın

---

## Adım 3: JSON Editor'ı Kullanın
1. **"Atlas Vector Search"** seçeneğini seçin
2. **"JSON Editor"** seçeneğini tercih edin
3. **"Next"** butonuna tıklayın

---

## Adım 4: Index Tanımını Yapıştırın

**Index Name:** `vector_index`

**JSON Configuration (UPDATED with MADDE-level metadata):**
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1024,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "metadata.source_file"
    },
    {
      "type": "filter",
      "path": "metadata.source_dir"
    },
    {
      "type": "filter",
      "path": "metadata.document_title"
    },
    {
      "type": "filter",
      "path": "metadata.document_type"
    },
    {
      "type": "filter",
      "path": "metadata.madde_number"
    },
    {
      "type": "filter",
      "path": "metadata.page"
    }
  ]
}
```

---

## Adım 5: Index'i Oluşturun
1. **"Next"** butonuna tıklayın
2. **"Create Search Index"** butonuna tıklayın
3. ⏳ Index'in **"Active"** durumuna gelmesini bekleyin (1-2 dakika)

---

## Adım 6: Doğrulama

Index oluştuktan sonra test edin:

```bash
cd /Users/selcuk/Desktop/admin_pan/Legislation_RAG
python3 -c "from mongodb_vector_store import MongoDBVectorStore; store = MongoDBVectorStore(); results = store.similarity_search('iş sağlığı', k=3); print(f'✅ {len(results)} sonuç bulundu')"
```

---

## Önemli Notlar

### ✅ Doğru Ayarlar:
- **Index Name:** `vector_index` (config.py'deki MONGO_VECTOR_INDEX_NAME ile aynı olmalı)
- **Vector Dimensions:** 1024 (Voyage AI voyage-law-2 modeli)
- **Similarity:** cosine
- **Collection:** documents

### ⚠️ Dikkat Edilmesi Gerekenler:
- Index'in aktif hale gelmesi 1-2 dakika sürer
- Index adı `config.py`'deki `MONGO_VECTOR_INDEX_NAME` ile eşleşmeli
- Embedding boyutu (1024) Voyage AI model çıktısı ile uyumlu olmalı

---

## Alternatif: MongoDB Shell ile Oluşturma

Eğer Atlas UI kullanamıyorsanız, `mongosh` ile de oluşturabilirsiniz:

```javascript
use mevzuat_db;

db.documents.createSearchIndex(
  "vector_index",
  "vectorSearch",
  {
    fields: [
      {
        type: "vector",
        path: "embedding",
        numDimensions: 1024,
        similarity: "cosine"
      },
      {
        type: "filter",
        path: "metadata.source_file"
      },
      {
        type: "filter",
        path: "metadata.source_dir"
      },
      {
        type: "filter",
        path: "metadata.document_title"
      },
      {
        type: "filter",
        path: "metadata.document_type"
      },
      {
        type: "filter",
        path: "metadata.madde_number"
      },
      {
        type: "filter",
        path: "metadata.page"
      }
    ]
  }
);
```

---

## Sorun Giderme

### Problem: "Attribute mappings missing" hatası
**Çözüm:** PyMongo API yerine Atlas UI kullanın (yukarıdaki adımlar)

### Problem: Index oluştu ama çalışmıyor
**Çözüm:** 
1. Index'in **"Active"** durumda olduğundan emin olun
2. 2-3 dakika bekleyin
3. Index adını kontrol edin: `vector_index`

### Problem: Embedding boyutu uyuşmuyor
**Çözüm:** 
```python
# Mevcut model boyutunu kontrol edin:
python3 -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('./models/embedding_model'); print(f'Embedding boyutu: {model.get_sentence_embedding_dimension()}')"
```

---

## Index Oluştuktan Sonra

1. ✅ Flask API'yi test edin:
```bash
cd /Users/selcuk/Desktop/admin_pan/Legislation_RAG
python3 simple_server.py
```

2. ✅ Health endpoint'i kontrol edin:
```bash
curl http://localhost:8000/health
```

3. ✅ Query test edin:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "işveren yükümlülükleri nelerdir?"}'
```

---

## Özet: MongoDB Integration Tamamlandı ✅

**Tamamlanan:**
- ✅ 6,298 döküman MongoDB'de (embeddings ile)
- ✅ MongoDB Vector Store implementasyonu hazır
- ✅ Flask API MongoDB kullanıyor (Chroma değil)
- ✅ RAG pipeline MongoDB ile entegre

**Yapılması Gereken:**
- ⏳ MongoDB Atlas'ta Vector Search Index oluşturma (bu rehberdeki adımlar)
- ⏳ Index aktif olduktan sonra test etme

**Railway Deployment:**
- 🚀 Index oluştuktan sonra Railway'e deploy edebilirsiniz
- 🔑 Environment variables: MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME, MONGO_VECTOR_INDEX_NAME
