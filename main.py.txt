"""
Main entry point for the RAG system - CLI version

MongoDB Vector Store Version - Optimized for Railway Deployment

Usage:
    python main.py
"""

import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Import modules
from client import create_openrouter_client
from mongodb_vector_store import get_mongodb_vectorstore, mongodb_store_exists
from reranker import RerankerService
from rag_pipeline import RAGPipeline
from cli import run_cli


def main():
    """Main function to initialize and run the RAG system"""
    
    print("🚀 Initializing Legislation RAG System (MongoDB)...\n")
    
    # 1. MongoDB'de veri var mı kontrol et
    if not mongodb_store_exists():
        print("❌ MongoDB'de döküman bulunamadı!")
        print("💡 Lütfen önce preprocessing.py scriptini yerel bilgisayarınızda çalıştırın.")
        print("   python preprocessing.py")
        return
    
    # 2. Create OpenRouter client
    client = create_openrouter_client()
    
    # 3. MongoDB Vector Store'u yükle (ChromaDB yerine)
    vectorstore = get_mongodb_vectorstore()
    stats = vectorstore.get_collection_stats()
    print(f"✅ MongoDB bağlantısı başarılı: {stats['total_documents']} döküman yüklü\n")
    
    # 4. Initialize reranker
    reranker = RerankerService()
    
    # 5. Create RAG pipeline
    rag_pipeline = RAGPipeline(client, vectorstore, reranker)
    
    print("\n✅ Legislation RAG system ready!\n")
    
    # 6. Run CLI interface
    run_cli(rag_pipeline)


if __name__ == "__main__":
    main()
