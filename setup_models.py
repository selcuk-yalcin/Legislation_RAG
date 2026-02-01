#!/usr/bin/env python3
"""
Model Setup Script
Bu script, tüm gerekli modelleri önceden indirir.
Railway deployment'ta build aşamasında çalıştırılabilir.
"""

import os
from pathlib import Path
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from flashrank import Ranker
from config import EMBEDDING_MODEL, RERANKER_MODEL, FLASHRANK_CACHE_DIR, MODEL_CACHE_DIR

# ChromaDB telemetri kapatma
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_IMPL"] = "none"
os.environ["POSTHOG_DISABLED"] = "1"

def setup_models():
    """Tüm modelleri önceden indir"""
    
    print("🔧 Model kurulum başlıyor...")
    print("=" * 60)
    
    # 1. Embedding Model
    print("\n📥 1/2: Embedding model indiriliyor...")
    print(f"Model: {EMBEDDING_MODEL}")
    
    models_dir = Path(MODEL_CACHE_DIR)
    models_dir.mkdir(exist_ok=True)
    
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        cache_folder=MODEL_CACHE_DIR
    )
    print("✅ Embedding model hazır!")
    
    # Test embedding
    test_text = "Test metni"
    _ = embeddings.embed_query(test_text)
    print("✅ Embedding model test edildi!")
    
    # 2. Reranker Model
    print("\n📥 2/2: Reranker model indiriliyor...")
    print(f"Model: {RERANKER_MODEL}")
    
    flashrank_dir = Path(FLASHRANK_CACHE_DIR)
    flashrank_dir.mkdir(exist_ok=True)
    
    ranker = Ranker(
        model_name=RERANKER_MODEL,
        cache_dir=FLASHRANK_CACHE_DIR
    )
    print("✅ Reranker model hazır!")
    
    print("\n" + "=" * 60)
    print("✅ Tüm modeller başarıyla indirildi!")
    print("\nModeller şu dizinlerde:")
    print(f"  📁 Embedding: {MODEL_CACHE_DIR}")
    print(f"  📁 Reranker: {FLASHRANK_CACHE_DIR}")
    print("\n💡 Artık ana uygulama bu modelleri diskten okuyacak.")
    print("\n📦 Railway Volume kullanıyorsanız:")
    print(f"  - Volume mount: /app/data_persistent")
    print(f"  - Models: {MODEL_CACHE_DIR}")
    print(f"  - Cache: {FLASHRANK_CACHE_DIR}")

if __name__ == "__main__":
    setup_models()
