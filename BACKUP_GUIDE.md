# 📦 Kılavuz Backup ve Arşivleme Sistemi

## 🎯 Amaç
Klavuz dosyalarını **3 katmanlı yedekleme** ile korumak:
1. **MongoDB** - Hızlı vector search için (production database)
2. **Local PC** - JSON/Markdown dosyaları olarak (kolay inceleme)
3. **Azure Blob Storage** - Cloud arşiv (güvenli yedek)

## 📂 Veri Akışı

```
PDF Dosyalar (data/KLAVUZLAR/)
         ↓
Azure Document Intelligence (parsing)
         ↓
MongoDB Atlas (vector search)
         ↓
Export Tool (JSON + Markdown)
         ↓
┌────────────────────┬─────────────────────┐
│  Local PC          │  Azure Blob         │
│  (guides_output/)  │  (cloud backup)     │
└────────────────────┴─────────────────────┘
```

## 🛠️ Kurulum

### 1. Azure Blob Storage Setup

Azure Portal'dan:
1. Storage Account oluştur (örn: `isgklavuzlar`)
2. Container oluştur (örn: `klavuzlar-backup`)
3. Connection String'i al: Storage Account → Access Keys → Connection String

### 2. Environment Variables

`.env` dosyasına ekle:

```bash
# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=isgklavuzlar;AccountKey=xxxxx;EndpointSuffix=core.windows.net"
AZURE_STORAGE_CONTAINER="klavuzlar-backup"
```

### 3. Python Package Kurulumu

```bash
pip install azure-storage-blob
```

## 📥 Kullanım

### Seçenek 1: Full Export + Azure Backup (Önerilen)

Tüm kılavuzları export et VE Azure'a yükle:

```bash
cd Legislation_RAG
python export_guides.py
```

Menüden seçim yapın:
- Option **1**: Full export (JSON + MD + Summary + Azure)
- Embeddings include? **n** (dosya boyutunu küçük tutar)
- Upload to Azure? **y**

### Seçenek 2: Sadece Azure Backup

Mevcut local dosyaları Azure'a yükle:

```bash
python export_guides.py
```

Menüden **6** seç (Azure Backup only)

### Seçenek 3: Manuel Azure Upload

```bash
python azure_backup_manager.py
```

## 📊 Çıktı Formatları

### 1. Local PC (`guides_output/`)

```
guides_output/
├── guides_summary.json          # Tüm kılavuzların özeti
├── sample_chunks.json            # İlk 5 chunk örneği
│
├── json/                         # Her kılavuz ayrı JSON
│   ├── acil-durum-planı.json
│   ├── asbestle-çalışmalarda.json
│   └── ...
│
└── markdown/                     # Her kılavuz ayrı Markdown
    ├── acil-durum-planı.md
    ├── asbestle-çalışmalarda.md
    └── ...
```

### 2. Azure Blob Storage

```
klavuzlar-backup/
├── backups/
│   ├── 20260212_143022/           # Timestamp'li snapshot
│   │   ├── backup_metadata.json
│   │   ├── guides_summary.json
│   │   ├── sample_chunks.json
│   │   ├── json/
│   │   │   ├── acil-durum-planı.json
│   │   │   └── ...
│   │   └── markdown/
│   │       ├── acil-durum-planı.md
│   │       └── ...
│   │
│   └── 20260212_160000/           # Başka bir snapshot
│       └── ...
│
└── latest/                        # En güncel versiyon (timestamp yok)
    └── ...
```

## 🔍 Azure'dan Dosya İndirme

### Azure Portal'dan:
1. Storage Account → Containers → klavuzlar-backup
2. Backup klasörünü seç (örn: `backups/20260212_143022/`)
3. İstediğin dosyaya sağ tıkla → Download

### Azure Storage Explorer (Tavsiye):
- Ücretsiz GUI tool: https://azure.microsoft.com/en-us/products/storage/storage-explorer/
- Drag & drop ile toplu indirme
- Arama ve filtreleme

### Azure CLI:
```bash
# Container'daki tüm dosyaları listele
az storage blob list --container-name klavuzlar-backup --account-name isgklavuzlar

# Belirli bir backup'ı indir
az storage blob download-batch \
  --source klavuzlar-backup \
  --destination ./downloaded_backup \
  --pattern "backups/20260212_143022/*"
```

## 📋 Backup Metadata

Her backup'ta `backup_metadata.json` oluşturulur:

```json
{
  "timestamp": "20260212_143022",
  "backup_time": "2026-02-12T14:30:22.123456",
  "file_count": 12,
  "files": [
    "https://isgklavuzlar.blob.core.windows.net/klavuzlar-backup/backups/20260212_143022/guides_summary.json",
    "https://isgklavuzlar.blob.core.windows.net/klavuzlar-backup/backups/20260212_143022/json/acil-durum.json",
    ...
  ],
  "blob_prefix": "backups/20260212_143022",
  "container": "klavuzlar-backup"
}
```

## 💡 Best Practices

### 1. Düzenli Backup Zamanlaması
```bash
# Her gün 02:00'de otomatik backup (cron job)
0 2 * * * cd /path/to/Legislation_RAG && python export_guides.py << EOF
1
n
y
EOF
```

### 2. Versiyon Kontrolü
- Timestamp'li snapshot'lar ile eski versiyonlar korunur
- `latest/` klasörü her zaman en güncel veriyi içerir
- Eski snapshot'ları manuel silebilirsiniz

### 3. Maliyeti Düşük Tutma
- JSON export'ta **embeddings dahil etmeyin** (1024-dim = büyük dosya)
- Cool/Archive tier kullanın (sık erişilmeyen veriler için)
- Lifecycle policy ile eski backup'ları otomatik sil

### 4. Güvenlik
- Connection String'i **asla GitHub'a pushlama**
- `.env` dosyasını `.gitignore`'a ekle
- Shared Access Signature (SAS) kullan (production'da)

## 🧪 Test

Azure backup'ı test et:

```bash
python azure_backup_manager.py
```

Çıktı:
```
✅ Container exists: klavuzlar-backup
📋 Existing backups:
   - backups/20260212_143022/backup_metadata.json
   - backups/20260212_143022/guides_summary.json
   ...
✅ Found local exports: /Users/selcuk/Desktop/admin_pan/Legislation_RAG/guides_output
🤔 Create backup snapshot? (y/n): 
```

## ❓ Sık Sorulan Sorular

### MongoDB'den silersem Azure'dan geri yükleyebilir miyim?
Evet! JSON dosyalarını Azure'dan indir, MongoDB'ye tekrar upload et:
```bash
python upload_from_json.py guides_output/json/
```

### Backup maliyeti ne kadar?
- 75 kılavuz × ~100KB = ~7.5 MB
- Azure Blob (Hot tier): $0.0184/GB/ay = ~$0.0001/ay
- Bandwidth (download): İlk 5GB ücretsiz
- **Toplam**: Neredeyse bedava!

### Local dosyaları silsem sorun olur mu?
Hayır! Azure'da her zaman backup var. Tekrar export etmek için:
```bash
python export_guides.py
```

### Azure olmadan kullanabilir miyim?
Evet! Export tool Azure olmadan da çalışır:
- MongoDB → Local JSON/MD export
- Azure backup opsiyonel
- AZURE_STORAGE_CONNECTION_STRING yoksa sadece local'e kaydeder

## 🚀 Hızlı Başlangıç

```bash
# 1. Azure setup (sadece ilk kez)
# .env dosyasına connection string ekle

# 2. Package kurulumu
pip install azure-storage-blob

# 3. Full export + backup
cd Legislation_RAG
python export_guides.py

# 4. Seçenekleri işaretle:
# [1] Full export
# [n] No embeddings
# [y] Upload to Azure

# 5. Kontrol et
# Local: guides_output/ klasörü
# Azure: Storage Explorer ile kontrol
```

## 📞 Destek

Sorun mu yaşıyorsun?

1. Test script çalıştır: `python azure_backup_manager.py`
2. Connection string kontrol et: `.env` dosyası
3. Container var mı kontrol et: Azure Portal
4. Hata mesajlarını incele: Terminal output

---

**Son Güncelleme**: 12 Şubat 2026  
**Versiyon**: 1.0
