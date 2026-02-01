"""
Configuration settings for the RAG system
"""

import os

# Try to load .env file for local development (Railway doesn't need this)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Railway doesn't have python-dotenv, use system env vars directly

# Debug: Environment variables kontrolü
print("=" * 70)
print("🔧 Configuration Loading...")
print("=" * 70)

# API Configuration - Railway'de system environment variables'dan okunur
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY") or os.getenv("VOYAGE_API_KEY")

# MongoDB Configuration - Railway'de MUTLAKA set edilmeli
MONGO_URI = os.environ.get("MONGO_URI") or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME") or os.getenv("MONGO_DB_NAME", "mevzuat_db")
MONGO_COLLECTION_NAME = os.environ.get("MONGO_COLLECTION_NAME") or os.getenv("MONGO_COLLECTION_NAME", "documents")
MONGO_VECTOR_INDEX_NAME = os.environ.get("MONGO_VECTOR_INDEX_NAME") or os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")

# Debug output
print(f"📊 MONGO_URI: {MONGO_URI[:50] if MONGO_URI else 'NOT SET'}...")
print(f"📊 MONGO_DB_NAME: {MONGO_DB_NAME}")
print(f"📊 OPENROUTER_API_KEY: {'✅ Set' if OPENROUTER_API_KEY else '❌ Not Set'}")
print(f"📊 VOYAGE_API_KEY: {'✅ Set' if VOYAGE_API_KEY else '❌ Not Set'}")
print("=" * 70)

# Railway environment check
if not VOYAGE_API_KEY:
    print("⚠️  WARNING: VOYAGE_API_KEY not found!")
if MONGO_URI == "mongodb://localhost:27017/":
    print("⚠️  WARNING: Using default localhost MongoDB - check Railway environment variables!")

# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-3.5-turbo")  # OpenRouter üzerinden
VOYAGE_EMBEDDING_MODEL = os.getenv("VOYAGE_EMBEDDING_MODEL", "voyage-law-2")  # Voyage AI embedding
VOYAGE_RERANK_MODEL = os.getenv("VOYAGE_RERANK_MODEL", "rerank-2")  # Voyage AI reranking

# Legacy Model Configuration (DEACTIVATED - kept for backward compatibility)
# EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
# RERANKER_MODEL = os.getenv("RERANKER_MODEL", "ms-marco-MiniLM-L-12-v2")
# MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./models")
# FLASHRANK_CACHE_DIR = os.getenv("FLASHRANK_CACHE_DIR", "./flashrank_cache")

# Document Configuration
DATA_DIR = "./data"  # Ana data klasörü
KANUN_DIR = "./data/KANUN VE YÖNETMELİKLER"  # Kanunlar ve yönetmelikler
TEBLIG_DIR = "./data/TEBLİĞ"  # Tebliğler

# RAG Parameters
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
INITIAL_RETRIEVAL_K = 50
TOP_RERANKED_K = 15

# LLM Parameters
TEMPERATURE = 0.2
MAX_TOKENS = 1500
EXPANSION_TEMPERATURE = 0.3
EXPANSION_MAX_TOKENS = 100

# Conversation Memory Configuration
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))  # Son 10 mesaj (5 soru + 5 cevap)
MEMORY_STRATEGY = os.getenv("MEMORY_STRATEGY", "sliding_window")  # sliding_window veya summarize

# Vector Store Configuration
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "documents")

# HTTP Client Configuration
HTTP_TIMEOUT = 60.0
