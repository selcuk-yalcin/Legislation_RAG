# 🚂 Railway Deployment Guide - Legislation RAG API

## 📋 Ön Hazırlık (LOCAL - Tek Seferlik)

### 1. PDF'leri MongoDB'ye Yükle (LOCAL'de yapıldı ✅)
```bash
cd Legislation_RAG
python3 document_loader.py
```

**Sonuç:**
- ✅ 6,298 chunk MongoDB'ye yüklendi
- ✅ Her chunk için 384-boyutlu embedding oluşturuldu
- ✅ MongoDB Atlas'ta saklanıyor

---

## 🚀 Railway Deployment

### Adım 1: Railway Projesi Oluştur

1. [Railway.app](https://railway.app) → Login
2. **"New Project"** → **"Deploy from GitHub repo"**
3. Repository seç: `admin_pan`
4. Root directory: `/Legislation_RAG` (önemli!)

### Adım 2: Environment Variables Ekle

Railway Dashboard → **Variables** sekmesi:

```env
# MongoDB Connection (ZORUNLU)
MONGO_URI=mongodb+srv://<username>:<password>@mevzuatdb.qqpyi1b.mongodb.net/?appName=mevzuatdb
MONGO_DB_NAME=mevzuat_db
MONGO_COLLECTION_NAME=documents
MONGO_VECTOR_INDEX_NAME=vector_index

# OpenRouter API (RAG için ZORUNLU)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Embedding Model (Otomatik indirilecek)
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Model Cache (Railway volume)
MODEL_CACHE_DIR=/app/models
FLASHRANK_CACHE_DIR=/app/flashrank_cache

# LLM Configuration
MODEL_NAME=ai21/jamba-mini-1.7
TEMPERATURE=0.2
MAX_TOKENS=1500
```

### Adım 3: Deploy Settings

Railway Dashboard → **Settings**:

- **Start Command:** `bash railway_start.sh`
- **Health Check Path:** `/health`
- **Region:** `us-west1` (veya size yakın)

### Adım 4: Deploy!

```bash
git add .
git commit -m "feat: Railway deployment with MongoDB embeddings"
git push origin main
```

Railway otomatik deploy edecek! 🚀

---

## ✅ Deployment Sonrası Test

### 1. Health Check
```bash
curl https://your-app.railway.app/health
```

Beklenen:
```json
{
  "status": "healthy",
  "message": "Legislation RAG System (MongoDB)",
  "mongodb": {
    "connected": true,
    "total_documents": 6298
  }
}
```

### 2. Stats Check
```bash
curl https://your-app.railway.app/stats
```

Beklenen:
```json
{
  "total_documents": 6298,
  "database": "mevzuat_db",
  "collection": "documents",
  "status": "success"
}
```

### 3. Query Test
```bash
curl -X POST https://your-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Yüksekte çalışma güvenliği nedir?"}'
```

---

## 🔧 Troubleshooting

### Model İndirme Yavaşsa

İlk deployment'ta model indirme ~2-3 dakika sürebilir.

**Çözüm:** Railway logs'da kontrol edin:
```bash
railway logs
```

Görmeli: `Loading model: sentence-transformers/...`

### MongoDB Bağlantı Hatası

**Kontrol:**
1. `MONGO_URI` doğru mu?
2. MongoDB Atlas'ta IP whitelist: `0.0.0.0/0` (herkese açık)
3. MongoDB user/password doğru mu?

### Memory Hatası

Embedding model ~500MB RAM kullanır.

**Çözüm:** Railway plan upgrade gerekebilir (Hobby → Pro)

---

## 📊 Railway Resource Usage

**Tahmini Kullanım:**
- **Memory:** ~800MB (model + API)
- **CPU:** Düşük (sorgu geldiğinde artar)
- **Disk:** ~200MB (kod + dependencies)
- **Bandwidth:** Sınırsız

**Model Cache:** 
- İlk başlatmada indirilir
- Railway volume'de saklanır
- Tekrar başlatmalarda hızlı yükle

nir

---

## 🔗 Admin Panel Bağlantısı

Railway URL'ini aldıktan sonra Admin Panel'e ekle:

**Admin/.env:**
```env
VITE_LEGISLATION_API_URL=https://your-app.railway.app
```

---

## 📝 Önemli Notlar

1. ✅ **PDF dosyaları Git'e atılmadı** (data/ klasörü local)
2. ✅ **Model dosyaları Git'e atılmadı** (models/ ignore edildi)
3. ✅ **Embeddings MongoDB'de** (Railway'de tekrar oluşturulmayacak)
4. ✅ **Sadece API deploy ediliyor** (minimal footprint)

---

## 🎯 Sonuç

Railway'de sadece şunlar var:
- Flask API kodu
- MongoDB bağlantısı
- Model otomatik indirilecek
- Embeddings hazır (MongoDB'de)

**Boyut:** ~100MB (kod + dependencies)
**Startup:** ~30 saniye (ilk kez ~2 dakika)

Başarılar! 🚀
