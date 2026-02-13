"""
Configuration settings for the RAG system - OPTIMIZED FOR 2026
"""

import os

# Try to load .env file for local development (Railway doesn't need this)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  

# Debug: Environment variables kontrolü
print("=" * 70)
print("🔧 Configuration Loading (Optimized for Legal RAG)...")
print("=" * 70)

# API Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY") or os.getenv("VOYAGE_API_KEY")

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI") or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME") or os.getenv("MONGO_DB_NAME", "mevzuat_db")
MONGO_COLLECTION_NAME = os.environ.get("MONGO_COLLECTION_NAME") or os.getenv("MONGO_COLLECTION_NAME", "documents")
MONGO_VECTOR_INDEX_NAME = os.environ.get("MONGO_VECTOR_INDEX_NAME") or os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")

# Arize Phoenix Tracing Configuration
ARIZE_SPACE_ID = os.environ.get("ARIZE_SPACE_ID", "")
ARIZE_API_KEY = os.environ.get("ARIZE_API_KEY", "")
ARIZE_PROJECT_NAME = os.environ.get("ARIZE_PROJECT_NAME", "legislationchatbot")

# Web Fallback Configuration (Serper + Azure DI)
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
AZURE_DI_ENDPOINT = os.environ.get("AZURE_DI_ENDPOINT", "")
AZURE_DI_KEY = os.environ.get("AZURE_DI_KEY", "")
AZURE_DI_MODEL = os.environ.get("AZURE_DI_MODEL", "prebuilt-layout")
TR_PROXY_URL = os.environ.get("TR_PROXY_URL", "")  # Optional: Turkey IP proxy

# Azure Blob Storage Configuration (for backup and archive)
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "klavuzlar-backup")

# Debug output
print(f"📊 MONGO_URI: {MONGO_URI[:30]}...")
print(f"📊 MONGO_DB_NAME: {MONGO_DB_NAME}")
print(f"📊 OPENROUTER_API_KEY: {'✅ Set' if OPENROUTER_API_KEY else '❌ Not Set'}")
print(f"📊 VOYAGE_API_KEY: {'✅ Set' if VOYAGE_API_KEY else '❌ Not Set'}")
print("=" * 70)

# --- MODEL SEÇİMLERİ (BAŞARI VE MALİYET ODAKLI) ---
# Gemini 2.5 Flash Lite: Google's latest fast and efficient model with 1M context
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemini-2.5-flash-lite") 

# Voyage-law-2: Hukuki metinler için optimize edilmiş 1024 boyutlu embedding modeli.
VOYAGE_EMBEDDING_MODEL = os.getenv("VOYAGE_EMBEDDING_MODEL", "voyage-law-2")

# Rerank-2.5-Lite: Yüksek hız ve 2.5 kat daha düşük maliyetle keskin sıralama sağlar.
VOYAGE_RERANK_MODEL = os.getenv("VOYAGE_RERANK_MODEL", "rerank-2.5-lite") 

# --- RAG PARAMETRELERİ (MEVZUAT İÇİN ÖZELLEŞTİRİLDİ) ---
# CHUNK_SIZE: Madde bütünlüğünü korurken odaklı kalmak için 1500 idealdir.
CHUNK_SIZE = 1500 

# CHUNK_OVERLAP: Madde geçişlerinde ve atıflarda bağlam kaybını önler.
CHUNK_OVERLAP = 300 

# INITIAL_RETRIEVAL_K: Reranker'a geniş aday havuzu sunarak 'iğneyi samanlıktan çıkarmayı' sağlar.
INITIAL_RETRIEVAL_K = 50

# TOP_RERANKED_K: LLM'e (GPT-4o-mini) gönderilen en kaliteli ve elenmiş parça sayısı.
TOP_RERANKED_K = 15

# RERANK_SCORE_THRESHOLD: Voyage Reranker skor eşiği (0.0-1.0)
# Alakasız ama kelime benzerliği olan dökümanları eler.
# Önerilen: 0.4-0.5 arası (yüksek kalite kontrolü için)
RERANK_SCORE_THRESHOLD = float(os.getenv("RERANK_SCORE_THRESHOLD", "0.45"))

# --- DOCUMENT PATHS ---
DATA_DIR = "./data"  # Ana data klasörü
KANUN_DIR = "./data/KANUN VE YÖNETMELİKLER"  # Kanunlar ve yönetmelikler
TEBLIG_DIR = "./data/TEBLİĞ"  # Tebliğler

# --- LLM VE HTTP PARAMETRELERİ ---
TEMPERATURE = 0.1  # Denetçi modu: düşük yaratıcılık, metne bağlılık
MAX_TOKENS = 800   # Kısa ve öz cevaplar için düşürüldü
EXPANSION_TEMPERATURE = 0.3
EXPANSION_MAX_TOKENS = 100

# HTTP_TIMEOUT: Rerank işlemi 100 döküman için yoğun olduğundan süre artırıldı.
HTTP_TIMEOUT = 90.0

# Bellek Yapılandırması
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))
MEMORY_STRATEGY = os.getenv("MEMORY_STRATEGY", "sliding_window")
