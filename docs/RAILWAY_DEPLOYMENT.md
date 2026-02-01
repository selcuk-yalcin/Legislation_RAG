# Railway Deployment Guide - Legislation RAG

## 🚂 Railway'e Deploy Etme Rehberi

Bu rehber, Legislation RAG sistemini Railway platformuna nasıl deploy edeceğinizi anlatır.

## 📋 Ön Gereksinimler

1. **Railway Hesabı**: [railway.app](https://railway.app) üzerinden ücretsiz hesap açın
2. **GitHub Repository**: Kodunuzu GitHub'a push edin
3. **OpenRouter API Key**: Mevcut API key'iniz

## 🚀 Deployment Adımları

### 1. Repository Hazırlığı

Kodunuz zaten hazır:
```bash
cd /Users/selcuk/Desktop/admin_pan/Legislation_RAG
```

**Gerekli Dosyalar:**
- ✅ `model/app.py` - Flask API
- ✅ `model/requirements.txt` - Python dependencies
- ✅ `model/Procfile` - Railway start komutu
- ✅ `model/runtime.txt` - Python versiyonu
- ✅ `model/railway.json` - Railway config
- ✅ `.gitignore` - Git ignore rules

### 2. GitHub'a Push

```bash
cd /Users/selcuk/Desktop/admin_pan/Legislation_RAG

# Git repo başlat (eğer yoksa)
git init
git add .
git commit -m "Initial commit: Multi-document Legislation RAG system"

# GitHub repo oluştur ve push et
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Legislation_RAG.git
git push -u origin main
```

### 3. Railway'de Proje Oluştur

1. [Railway Dashboard](https://railway.app/dashboard) → **New Project**
2. **Deploy from GitHub repo** seçin
3. `Legislation_RAG` repository'sini seçin
4. **Add variables** kısmına gidin

### 4. Environment Variables Ayarla

Railway dashboard'da **Variables** sekmesinden:

```bash
OPENROUTER_API_KEY=your_api_key_here
PORT=8080
```

**Not:** `PORT` Railway tarafından otomatik atanır, manuel eklemenize gerek yok.

### 5. Build Settings

Railway otomatik olarak algılar, ama kontrol için:

**Root Directory:**
```
/model
```

**Start Command:**
```bash
gunicorn app:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
```

### 6. Deploy!

Railway otomatik olarak deploy edecek. İlk deployment ~5-10 dakika sürebilir çünkü:
- Tüm dependencies yükleniyor
- 96 PDF dosyası işleniyor
- Vector database oluşturuluyor
- 6,298 chunk embed ediliyor

## 📊 Deployment Sonrası

### Railway URL

Railway size bir URL verecek:
```
https://legislation-rag-production.up.railway.app
```

### Test Etme

```bash
# Health check
curl https://your-app.railway.app/health

# Test sorusu
curl -X POST https://your-app.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "İşçi sağlık muayeneleri ne sıklıkta yapılır?"}'
```

### Admin Panel'i Bağla

Admin panelindeki `.env` dosyasını güncelleyin:

```bash
cd /Users/selcuk/Desktop/admin_pan/Admin

# .env dosyası oluştur/güncelle
echo "REACT_APP_LEGISLATION_API_URL=https://your-app.railway.app" > .env
```

## ⚙️ Railway Ayarları

### Önerilen Konfigürasyon

**Memory:** En az 2GB (ideal 4GB)
**CPU:** Shared (ücretsiz plan yeterli başlangıç için)

### Scaling

Railway ücretsiz plan:
- ✅ 500 saat/ay
- ✅ 8GB RAM
- ✅ Shared CPU

Yoğun kullanım için **Pro Plan** önerilir.

## 🔧 Sorun Giderme

### Deploy Hatası: Out of Memory

**Çözüm:** 
1. Railway dashboard → Settings → Increase memory
2. Veya `config.py` içinde chunk size'ı küçült:
```python
CHUNK_SIZE = 800  # 1000 yerine
```

### Timeout Hatası

**Çözüm:**
`Procfile` içinde timeout süresini artırın:
```
web: gunicorn app:app --workers 1 --timeout 300
```

### Data Klasörü Bulunamıyor

**Çözüm:**
Railway'de root directory ayarını kontrol edin:
```
Root Directory: /model
```

Ve `config.py` içinde path'leri kontrol edin:
```python
KANUN_DIR = "../data/KANUN VE YÖNETMELİKLER"
TEBLIG_DIR = "../data/TEBLİĞ"
```

### API Çalışıyor Ama Cevap Vermiyor

**Logs kontrol:**
Railway dashboard → Deployments → View Logs

Olası sorun: OpenRouter API key eksik veya hatalı.

## 📁 Dosya Yapısı (Railway için)

```
Legislation_RAG/
├── .gitignore           ✅ Railway tarafından ignore edilecekler
├── model/
│   ├── app.py          ✅ Flask API (main entry point)
│   ├── requirements.txt ✅ Dependencies
│   ├── runtime.txt     ✅ Python version
│   ├── Procfile        ✅ Start command
│   ├── railway.json    ✅ Railway config
│   ├── config.py       ✅ Yapılandırma
│   ├── document_loader.py
│   ├── vector_store.py
│   ├── rag_pipeline.py
│   └── ... (diğer modüller)
└── data/
    ├── KANUN VE YÖNETMELİKLER/  (86 PDF)
    └── TEBLİĞ/                   (10 PDF)
```

## 🎯 En İyi Pratikler

### 1. Environment Variables
- ✅ API keys'i Railway Variables'da sakla
- ❌ Asla kodda hardcode etme

### 2. Logs
- Railway logs'ları düzenli kontrol et
- Error tracking için Sentry entegre et

### 3. Caching
- Vector store'u cache'le (Railway persistent storage)
- FlashRank model'i cache'le

### 4. Performance
- İlk request yavaş olabilir (cold start)
- Warm-up endpoint ekle

## 🔄 Güncellemeler

Kod güncellemesi yaptığınızda:

```bash
git add .
git commit -m "Update: description"
git push origin main
```

Railway otomatik olarak yeni deployment yapacak.

## 💰 Maliyet Tahmini

**Ücretsiz Plan:**
- ✅ Development ve test için yeterli
- ✅ Düşük trafikli production kullanım

**Pro Plan ($20/ay):**
- ✅ Production kullanım
- ✅ 8GB RAM guarantee
- ✅ Dedicated CPU

## 📞 Destek

Railway sorunları için:
- [Railway Discord](https://discord.gg/railway)
- [Railway Docs](https://docs.railway.app)

---

## ✅ Checklist

Deployment öncesi kontrol:

- [ ] GitHub repository oluşturuldu
- [ ] Tüm gerekli dosyalar commit edildi
- [ ] `.gitignore` doğru ayarlandı
- [ ] OpenRouter API key hazır
- [ ] Railway hesabı açıldı
- [ ] Environment variables ayarlandı
- [ ] İlk deployment başlatıldı
- [ ] Health check testi yapıldı
- [ ] Admin panel bağlantısı test edildi

**Başarılı deployment sonrası:**
```
🎉 Legislation RAG sisteminiz Railway'de live!
📍 URL: https://your-app.railway.app
📊 96 dosya, 6,298 chunk hazır
✅ Admin panel bağlantısı aktif
```
