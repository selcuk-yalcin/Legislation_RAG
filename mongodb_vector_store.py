"""
MongoDB Vector Store - Production Ready (Voyage AI)
MongoDB Atlas Vector Search with Voyage AI embeddings.
"""

import os
from pymongo import MongoClient
import voyageai
from config import (
    MONGO_URI,
    MONGO_DB_NAME,
    MONGO_COLLECTION_NAME,
    MONGO_VECTOR_INDEX_NAME,
    VOYAGE_API_KEY,
    VOYAGE_EMBEDDING_MODEL
)


class MongoDBVectorStore:
    """MongoDB Atlas Vector Search Wrapper with Voyage AI"""
    
    def __init__(self):
        """Initialize MongoDB connection and Voyage AI client"""
        print("🔌 MongoDB Atlas'a bağlanılıyor...")
        print(f"   MONGO_URI: {MONGO_URI[:30]}...")  # Debug: İlk 30 karakter
        
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.collection = self.db[MONGO_COLLECTION_NAME]
        
        print("🤖 Voyage AI embedding client başlatılıyor...")
        if not VOYAGE_API_KEY:
            raise ValueError("❌ VOYAGE_API_KEY bulunamadı! Environment variable'ı kontrol edin.")
        
        self.voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
        self.embedding_model = VOYAGE_EMBEDDING_MODEL
        
        print(f"✅ MongoDB Vector Store hazır! Model: {self.embedding_model}")
    
    def similarity_search(self, query, k=10, filter_dict=None):
        """
        MongoDB Vector Search ile benzer dökümanları bul.
        
        Args:
            query (str): Arama sorgusu
            k (int): Döndürülecek döküman sayısı
            filter_dict (dict): Metadata filtreleri (opsiyonel)
            
        Returns:
            list: Document objelerinin listesi (LangChain formatında)
        """
        # 1. Sorguyu Voyage AI ile vektöre çevir
        result = self.voyage_client.embed([query], model=self.embedding_model, input_type="query")
        query_vector = result.embeddings[0]
        
        # 2. MongoDB Vector Search pipeline oluştur
        pipeline = [
            {
                "$vectorSearch": {
                    "index": MONGO_VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": k * 10,  # Daha iyi sonuçlar için fazla aday tara
                    "limit": k
                }
            },
            {
                "$project": {
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        # 3. Filter ekle (opsiyonel)
        if filter_dict:
            match_stage = {"$match": {}}
            for key, value in filter_dict.items():
                match_stage["$match"][f"metadata.{key}"] = value
            pipeline.insert(1, match_stage)
        
        # 4. Sorguyu çalıştır
        results = list(self.collection.aggregate(pipeline))
        
        # 5. LangChain Document formatına çevir
        documents = []
        for result in results:
            # Document benzeri obje oluştur
            doc = type('Document', (), {
                'page_content': result['content'],
                'metadata': result.get('metadata', {}),
                'score': result.get('score', 0)
            })()
            documents.append(doc)
        
        return documents
    
    def similarity_search_with_score(self, query, k=10, filter_dict=None):
        """
        Benzerlik skorları ile birlikte döküman döndür.
        
        Args:
            query (str): Arama sorgusu
            k (int): Döndürülecek döküman sayısı
            filter_dict (dict): Metadata filtreleri (opsiyonel)
            
        Returns:
            list: (Document, score) tuple'larının listesi
        """
        docs = self.similarity_search(query, k, filter_dict)
        return [(doc, doc.score) for doc in docs]
    
    def get_collection_stats(self):
        """Koleksiyon istatistiklerini döndür"""
        count = self.collection.count_documents({})
        return {
            "total_documents": count,
            "database": MONGO_DB_NAME,
            "collection": MONGO_COLLECTION_NAME
        }
    
    def health_check(self):
        """MongoDB bağlantısını kontrol et"""
        try:
            self.client.admin.command('ping')
            count = self.collection.count_documents({})
            return {
                "status": "healthy",
                "mongodb": "connected",
                "documents": count
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


def get_mongodb_vectorstore():
    """
    MongoDB Vector Store instance oluştur.
    ChromaDB yerine kullanılır.
    
    Returns:
        MongoDBVectorStore: Vector store instance
    """
    return MongoDBVectorStore()


def mongodb_store_exists():
    """
    MongoDB'de döküman var mı kontrol et.
    
    Returns:
        bool: True if documents exist
    """
    try:
        print(f"🔍 MongoDB kontrolü yapılıyor...")
        print(f"   MONGO_URI: {MONGO_URI[:50]}...")
        print(f"   MONGO_DB_NAME: {MONGO_DB_NAME}")
        print(f"   MONGO_COLLECTION_NAME: {MONGO_COLLECTION_NAME}")
        
        client = MongoClient(MONGO_URI)
        
        # MongoDB bağlantısını test et
        client.admin.command('ping')
        print("   ✅ MongoDB bağlantısı başarılı!")
        
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        count = collection.count_documents({})
        print(f"   ✅ {count} döküman bulundu!")
        return count > 0
    except Exception as e:
        print(f"❌ MongoDB bağlantı hatası: {e}")
        import traceback
        traceback.print_exc()
        return False
