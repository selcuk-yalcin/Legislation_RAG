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

# Debug output
print(f"📊 MONGO_URI: {MONGO_URI[:30]}...")
print(f"📊 MONGO_DB_NAME: {MONGO_DB_NAME}")
print(f"📊 OPENROUTER_API_KEY: {'✅ Set' if OPENROUTER_API_KEY else '❌ Not Set'}")
print(f"📊 VOYAGE_API_KEY: {'✅ Set' if VOYAGE_API_KEY else '❌ Not Set'}")
print("=" * 70)

# --- MODEL SEÇİMLERİ (BAŞARI VE MALİYET ODAKLI) ---
# GPT-4o-mini: 3.5 Turbo fiyatına çok daha yüksek zeka ve analiz kapasitesi sunar.
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini") 

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

# --- DOCUMENT PATHS ---
DATA_DIR = "./data"  # Ana data klasörü
KANUN_DIR = "./data/KANUN VE YÖNETMELİKLER"  # Kanunlar ve yönetmelikler
TEBLIG_DIR = "./data/TEBLİĞ"  # Tebliğler

# --- LLM VE HTTP PARAMETRELERİ ---
TEMPERATURE = 0.2
MAX_TOKENS = 1500
EXPANSION_TEMPERATURE = 0.3
EXPANSION_MAX_TOKENS = 100

# HTTP_TIMEOUT: Rerank işlemi 100 döküman için yoğun olduğundan süre artırıldı.
HTTP_TIMEOUT = 90.0

# Bellek Yapılandırması
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))
MEMORY_STRATEGY = os.getenv("MEMORY_STRATEGY", "sliding_window")
