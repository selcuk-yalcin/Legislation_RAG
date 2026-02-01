# 🧪 Tests

Bu klasörde Legislation RAG sisteminin test scriptleri bulunur.

## Test Dosyaları

### MongoDB & Vector Store Tests
- **`test_mongodb.py`** - MongoDB bağlantısı ve döküman sayısı kontrolü
- **`test_vector_search.sh`** - Vector search endpoint testi (curl)

### Memory Management Tests
- **`test_memory.py`** - Detaylı memory management testi
- **`test_memory_simple.py`** - Basit memory sliding window testi

### Source Citations Test
- **`test_sources.py`** - Kaynak formatı ve metadata gösterimi testi

### RAG System Tests
- **`test_rag_simple.py`** - Tam RAG pipeline testi (Python 3.9 uyumlu)
- **`test_ragas_quick.py`** - RAGAS quick test (Python 3.10+ gerekli)

### RAGAS Evaluation
- **`ragas_evaluation.py`** - Kapsamlı RAGAS evaluation (5 metrik, 5 test sorusu)

## Kullanım

```bash
# MongoDB test
python test_mongodb.py

# Memory test
python test_memory_simple.py

# Source citations test
python test_sources.py

# RAG system test (Python 3.9)
python test_rag_simple.py

# RAGAS evaluation (Python 3.10+ gerekli)
python ragas_evaluation.py
```

## Gereksinimler

- Python 3.9+ (test_rag_simple.py için)
- Python 3.10+ (RAGAS testleri için)
- MongoDB Atlas bağlantısı
- Environment variables (.env dosyası)

## Not

RAGAS testleri Python 3.10+ gerektiriyor. Python 3.9 kullanıyorsanız:

```bash
conda create -n ragas_env python=3.10
conda activate ragas_env
pip install -r ../requirements.txt
python ragas_evaluation.py
```
