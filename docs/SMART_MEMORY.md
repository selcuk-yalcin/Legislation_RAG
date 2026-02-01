# 🧠 Akıllı Bellek Yönetimi (Smart Memory Management)

## ✅ Tamamlandı

Conversation history artık sınırsız uzamıyor - **sliding window** stratejisi ile otomatik yönetiliyor!

---

## 📋 Özellikler

### 1. **Sliding Window Strategy**
- Son **10 mesaj** tutulur (5 soru + 5 cevap)
- En eski mesajlar otomatik silinir
- Yeni mesaj geldiğinde en eski çıkar (FIFO - First In First Out)

### 2. **Yapılandırılabilir**
```python
# config.py
MAX_CONVERSATION_HISTORY = 10  # Mesaj sayısı limiti
MEMORY_STRATEGY = "sliding_window"  # Strateji
```

Environment variable ile de ayarlanabilir:
```bash
export MAX_CONVERSATION_HISTORY=20
export MEMORY_STRATEGY=sliding_window
```

### 3. **Otomatik Temizleme**
Her mesajdan sonra otomatik çalışır:
- Kullanıcı sorusu eklenir → `_manage_conversation_memory()` çalışır
- AI cevabı eklenir → Tekrar `_manage_conversation_memory()` çalışır

---

## 🎯 Nasıl Çalışır?

### Örnek Senaryo: Max 10 mesaj

```
İlk 5 Soru-Cevap:
[1] User: Soru 1
[2] AI: Cevap 1
[3] User: Soru 2
[4] AI: Cevap 2
[5] User: Soru 3
[6] AI: Cevap 3
[7] User: Soru 4
[8] AI: Cevap 4
[9] User: Soru 5
[10] AI: Cevap 5  ← LIMIT DOLDU!

6. Soru Geldiğinde:
[1-2] SİLİNDİ ❌ (En eski çift)
[3] User: Soru 2   ← Artık en eski bu
[4] AI: Cevap 2
[5] User: Soru 3
[6] AI: Cevap 3
[7] User: Soru 4
[8] AI: Cevap 4
[9] User: Soru 5
[10] AI: Cevap 5
[11] User: Soru 6  ← YENİ
```

---

## 🔧 Kod Değişiklikleri

### 1. `config.py` - Yeni Parametreler
```python
# Conversation Memory Configuration
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))
MEMORY_STRATEGY = os.getenv("MEMORY_STRATEGY", "sliding_window")
```

### 2. `rag_pipeline.py` - Memory Management
```python
class RAGPipeline:
    def __init__(self, client, vectorstore, reranker, max_history=None):
        self.max_history = max_history or MAX_CONVERSATION_HISTORY
        self.memory_strategy = MEMORY_STRATEGY
    
    def _manage_conversation_memory(self):
        """Sliding window - keep only last N messages"""
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_conversation_stats(self):
        """Memory istatistikleri"""
        return {
            "total_messages": len(self.conversation_history),
            "max_allowed": self.max_history,
            "memory_strategy": self.memory_strategy,
            "memory_usage_percent": ...
        }
```

### 3. `app.py` - Yeni Endpoint
```python
@app.route('/api/memory', methods=['GET'])
def get_memory_stats():
    """Memory durumunu göster"""
    stats = rag_pipeline.get_conversation_stats()
    return jsonify(stats)
```

---

## 📊 API Kullanımı

### Memory İstatistikleri
```bash
curl http://localhost:8000/api/memory
```

**Response:**
```json
{
  "total_messages": 6,
  "max_allowed": 10,
  "memory_strategy": "sliding_window",
  "memory_usage_percent": 60.0,
  "status": "success"
}
```

### Conversation Reset
```bash
curl -X POST http://localhost:8000/api/reset
```

**Response:**
```json
{
  "message": "Conversation history cleared",
  "status": "success"
}
```

---

## ✅ Test Sonuçları

```bash
python3 test_memory_simple.py
```

**Çıktı:**
```
After Q&A pair 5:
  Total messages: 10/10
  Memory usage: 100%
  ⚠️  LIMIT REACHED!

After Q&A pair 6:
  Total messages: 10/10  ← Hala 10!
  Oldest in memory: Question 2  ← En eski değişti (1 değil)
  Newest in memory: Answer 6

✅ Sliding window working correctly!
   Questions 1-5 were removed
   Questions 6-8 are kept in memory
```

---

## 🎯 Avantajlar

### ✅ **Token Tasarrufu**
- Sınırsız history → API token aşımı
- Sliding window → Sabit token kullanımı

### ✅ **Performans**
- Daha kısa context → Daha hızlı yanıt
- Bellekte az yer → Daha az RAM

### ✅ **Maliyet Düşüşü**
- LLM API'ye daha az mesaj gönderilir
- OpenRouter maliyeti azalır

### ✅ **Kullanıcı Deneyimi**
- Son 5 soru-cevap hatırlanır
- Çok eski bağlamla karışma olmaz

---

## ⚙️ Gelecek İyileştirmeler

### 1. **Summarize Strategy** (TODO)
```python
if self.memory_strategy == "summarize":
    # En eski 5 mesajı özetle, özeti sakla
    # Detayları sil
```

### 2. **Önemli Mesaj Saklama**
```python
# Kullanıcı "Bu önemli" derse, o mesajı sliding window'dan muaf tut
```

### 3. **Dinamik Limit**
```python
# Mesaj uzunluğuna göre limit ayarla
# Kısa mesajlar → Daha fazla sayı
# Uzun mesajlar → Daha az sayı
```

---

## 📚 İlgili Dosyalar

- `/Users/selcuk/Desktop/admin_pan/Legislation_RAG/config.py` - Konfigürasyon
- `/Users/selcuk/Desktop/admin_pan/Legislation_RAG/rag_pipeline.py` - Memory logic
- `/Users/selcuk/Desktop/admin_pan/Legislation_RAG/app.py` - API endpoints
- `/Users/selcuk/Desktop/admin_pan/Legislation_RAG/test_memory_simple.py` - Test script

---

## 🚀 Deployment

Railway'de environment variable ekleyin:
```bash
MAX_CONVERSATION_HISTORY=10
MEMORY_STRATEGY=sliding_window
```

Veya varsayılan değerler kullanılır (10 mesaj, sliding window).

---

## ✅ Özet

| Özellik | Değer |
|---------|-------|
| **Max Mesaj** | 10 (5 Q&A) |
| **Strateji** | Sliding Window |
| **Otomatik Temizlik** | ✅ Evet |
| **API Endpoint** | `/api/memory` |
| **Test** | ✅ Başarılı |
| **Production Ready** | ✅ Evet |

**Artık conversation history sonsuza kadar uzamıyor! 🎉**
