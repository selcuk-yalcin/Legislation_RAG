# 🧪 RAGAS Evaluation Framework

**RAGAS** (RAG Assessment) kütüphanesi kullanılarak Legislation RAG sisteminin kalitesi periyodik olarak ölçülür.

## 📊 Ölçülen Metrikler

### 1. **Faithfulness (Sadakat)** 
- **Ne ölçer?** Cevabın kaynak dökümanlara ne kadar sadık olduğu
- **Neden önemli?** Hallucination (uydurma) tespiti için kritik
- **Hedef:** ≥ 0.8

### 2. **Answer Relevancy (İlgililik)**
- **Ne ölçer?** Cevabın soruyla ne kadar ilgili olduğu
- **Neden önemli?** Kullanıcı memnuniyeti ve doğruluk
- **Hedef:** ≥ 0.7

### 3. **Context Precision (Hassasiyet)**
- **Ne ölçer?** Retrieval sisteminin doğru dökümanları bulma yeteneği
- **Neden önemli?** Yanlış bilgi önleme
- **Hedef:** ≥ 0.7

### 4. **Context Recall (Hatırlama)**
- **Ne ölçer?** Tüm ilgili bilginin bulunup bulunmadığı
- **Neden önemli?** Eksik bilgi önleme
- **Hedef:** ≥ 0.7

### 5. **Context Relevancy (Bağlam İlgililikliliği)**
- **Ne ölçer?** Bağlamın soruyla ne kadar ilgili olduğu
- **Neden önemli?** Gereksiz bilgi filtrasyonu
- **Hedef:** ≥ 0.7

## 🚀 Kullanım

### Kurulum

```bash
# RAGAS ve bağımlılıklarını yükle
pip install ragas datasets

# Veya tüm requirements'ı yükle
pip install -r requirements.txt
```

### Evaluation Çalıştırma

```bash
# Basit kullanım
python ragas_evaluation.py

# Çıktı: evaluation_results/ragas_evaluation_YYYYMMDD_HHMMSS.json
```

### Örnek Çıktı

```
╔════════════════════════════════════════════════════════════════════╗
║                    RAGAS EVALUATION SYSTEM                         ║
╚════════════════════════════════════════════════════════════════════╝

🚀 RAG sistemini başlatıyorum...
✅ RAG sistemi hazır!

📝 Test dataset'i hazırlanıyor...
✅ 5 test sorusu hazır

══════════════════════════════════════════════════════════════════════
🧪 RAGAS Evaluation Başlıyor
══════════════════════════════════════════════════════════════════════

📝 5 test sorusu işleniyor...

[1/5] Soru: İşverenin iş sağlığı ve güvenliği konusundaki yükümlülü...
    ✓ Cevap alındı (1234 karakter)
    ✓ Context: 5 döküman

══════════════════════════════════════════════════════════════════════
📊 RAGAS Metrikleri Hesaplanıyor...
══════════════════════════════════════════════════════════════════════

══════════════════════════════════════════════════════════════════════
📊 RAGAS EVALUATION RAPORU
══════════════════════════════════════════════════════════════════════

📈 Metrik Skorları (0-1 arası, 1 en iyi):

Faithfulness (Sadakat)                  : 0.872 ████████████████████████████████████░░░░ 🟢 Mükemmel
Answer Relevancy (İlgililik)            : 0.765 ██████████████████████████████░░░░░░░░░░ 🟡 İyi
Context Precision (Hassasiyet)          : 0.691 ███████████████████████████░░░░░░░░░░░░░ 🟡 İyi
Context Recall (Hatırlama)              : 0.723 ████████████████████████████░░░░░░░░░░░░ 🟡 İyi
Context Relevancy (Bağlam İlgililk...)  : 0.804 ████████████████████████████████░░░░░░░░ 🟢 Mükemmel

──────────────────────────────────────────────────────────────────────
GENEL ORTALAMA                          : 0.771
──────────────────────────────────────────────────────────────────────

💾 Sonuçlar kaydedildi: evaluation_results/ragas_evaluation_20250112_143022.json

✅ Evaluation tamamlandı!
```

## 📁 Çıktı Dosyası Formatı

```json
{
  "timestamp": "20250112_143022",
  "date": "2025-01-12T14:30:22.123456",
  "num_test_cases": 5,
  "metrics": {
    "faithfulness": 0.872,
    "answer_relevancy": 0.765,
    "context_precision": 0.691,
    "context_recall": 0.723,
    "context_relevancy": 0.804
  },
  "test_cases": [
    {
      "question": "İşverenin iş sağlığı ve güvenliği konusundaki...",
      "ground_truth": "İşveren, çalışanların iş sağlığı ve güvenliğini..."
    }
  ]
}
```

## 🎯 Skor Yorumlama

| Skor Aralığı | Rating | Durum | Aksiyon |
|--------------|--------|-------|---------|
| 0.8 - 1.0 | 🟢 Mükemmel | Sistem iyi çalışıyor | Sürdür |
| 0.6 - 0.8 | 🟡 İyi | Kabul edilebilir | İzle |
| 0.4 - 0.6 | 🟠 Orta | İyileştirme gerekli | Optimize et |
| 0.0 - 0.4 | 🔴 Düşük | Ciddi sorun var | Acil müdahale |

## 🔧 İyileştirme Önerileri

### Faithfulness Düşükse (< 0.7)
**Sorun:** LLM uydurma yapıyor, kaynaklara sadık kalmıyor

**Çözümler:**
```python
# config.py - Prompt'u güçlendir
SYSTEM_PROMPT = """
Sen bir mevzuat asistanısın.
SADECE verilen kaynaklardaki bilgileri kullan.
Kaynaklarda olmayan bilgi verme.
Emin değilsen 'Bu bilgi kaynaklarda yok' de.
"""

# rag_pipeline.py - Temperature düşür
temperature=0.2  # Daha deterministik
```

### Answer Relevancy Düşükse (< 0.7)
**Sorun:** Cevaplar konudan sapıyor

**Çözümler:**
```python
# query_expansion.py - Daha odaklı expansion
EXPANSION_PROMPT = """
Soruyu SADECE yasal terimlerle genişlet.
Konudan sapma.
"""

# config.py - Query expansion'ı azalt
MAX_EXPANDED_QUERIES = 2  # 3'ten düşür
```

### Context Precision Düşükse (< 0.7)
**Sorun:** Yanlış dökümanlar alınıyor

**Çözümler:**
```python
# config.py - Reranking güçlendir
FINAL_TOP_K = 3  # Daha az ama daha doğru
RERANK_SCORE_THRESHOLD = 0.5  # Eşiği yükselt

# mongodb_vector_store.py - Similarity threshold ekle
if score < 0.7:  # Düşük skorlu dökümanları filtrele
    continue
```

### Context Recall Düşükse (< 0.7)
**Sorun:** İlgili bilgiler kaçırılıyor

**Çözümler:**
```python
# config.py - Daha fazla döküman al
INITIAL_RETRIEVAL_K = 100  # 50'den artır

# mongodb_vector_store.py - numCandidates artır
"numCandidates": k * 20  # 10'dan artır
```

## 📅 Periyodik Evaluation

### Manuel Çalıştırma
```bash
# Her deployment öncesi
python ragas_evaluation.py

# Sonuçları karşılaştır
ls -lh evaluation_results/
```

### Otomatik Çalıştırma (İsteğe Bağlı)

**Cron Job (Her hafta)**
```bash
# crontab -e
0 9 * * 1 cd /path/to/Legislation_RAG && python ragas_evaluation.py
```

**CI/CD Pipeline (Her deployment)**
```yaml
# .github/workflows/deploy.yml
- name: Run RAGAS Evaluation
  run: |
    python ragas_evaluation.py
    # Sonuçları Slack'e gönder
```

**Flask Endpoint (API ile)**
```python
# app.py
@app.route('/api/evaluate', methods=['POST'])
def run_evaluation():
    # Admin auth required
    evaluator = RAGEvaluator()
    results = evaluator.run_evaluation()
    return jsonify(results)
```

## 🧪 Test Dataset Genişletme

```python
# ragas_evaluation.py - create_test_dataset()

# Daha fazla test sorusu ekle
test_cases = [
    {
        "question": "Yeni soru buraya...",
        "ground_truth": "Beklenen cevap buraya..."
    },
    # ... 50+ soru olana kadar ekle
]

# Gerçek kullanıcı sorularından oluştur
# app.py'de log'lanan soruları kullan
```

## 📈 Sonuçları İzleme

```python
import json
import glob
import matplotlib.pyplot as plt

# Tüm evaluation sonuçlarını oku
results = []
for file in sorted(glob.glob("evaluation_results/*.json")):
    with open(file) as f:
        results.append(json.load(f))

# Zaman içinde metrik trendlerini görselleştir
dates = [r['date'] for r in results]
faithfulness = [r['metrics']['faithfulness'] for r in results]

plt.plot(dates, faithfulness, label='Faithfulness')
plt.axhline(y=0.8, color='r', linestyle='--', label='Target')
plt.legend()
plt.show()
```

## ⚠️ Dikkat Edilecekler

1. **OpenRouter API Kullanımı**: Her evaluation OpenRouter API call yapar (maliyet)
2. **MongoDB Bağlantı**: Vector Search Index aktif olmalı
3. **Test Dataset**: Ground truth'ları iyi tanımla
4. **Sonuç Yorumlama**: Tek başına skor yetmez, trendlere bak

## 🎓 Kaynaklar

- [RAGAS Documentation](https://docs.ragas.io/)
- [RAGAS Metrics Explained](https://docs.ragas.io/en/latest/concepts/metrics/index.html)
- [RAG Evaluation Best Practices](https://www.rungalileo.io/blog/mastering-rag-evaluation)

---

**Sonraki Adım:** `python ragas_evaluation.py` çalıştır ve sistemin kalitesini ölç! 🚀
