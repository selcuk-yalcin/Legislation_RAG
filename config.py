"""
Configuration settings for the RAG system
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "mevzuat_db")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "documents")
MONGO_VECTOR_INDEX_NAME = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")

# Model Configuration
MODEL_NAME = "ai21/jamba-mini-1.7"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "ms-marco-MiniLM-L-12-v2")

# Model Cache Directories (Railway Volume support)
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./models")
FLASHRANK_CACHE_DIR = os.getenv("FLASHRANK_CACHE_DIR", "./flashrank_cache")

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
