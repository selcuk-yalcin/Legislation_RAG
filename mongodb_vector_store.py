"""
MongoDB Vector Store - Production Ready
MongoDB Atlas Vector Search implementation.
"""

import os
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from config import (
    MONGO_URI,
    MONGO_DB_NAME,
    MONGO_COLLECTION_NAME,
    MONGO_VECTOR_INDEX_NAME,
    MODEL_CACHE_DIR,
    EMBEDDING_MODEL
)


class MongoDBVectorStore:
    """MongoDB Atlas Vector Search Wrapper"""
    
    def __init__(self):
        """Initialize MongoDB connection and embedding model"""
        print("🔌 MongoDB Atlas'a bağlanılıyor...")
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.collection = self.db[MONGO_COLLECTION_NAME]
        
        print("🤖 Embedding modeli yükleniyor...")
        # Modeli yerel klasörden yükle (internetten indirmez!)
        model_path = os.path.join(MODEL_CACHE_DIR, "embedding_model")
        
        if os.path.exists(model_path):
            print(f"✅ Model yerel klasörden yükleniyor: {model_path}")
            self.model = SentenceTransformer(model_path)
        else:
            print(f"⚠️  Yerel model bulunamadı, indiriliyor: {EMBEDDING_MODEL}")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
        
        print("✅ MongoDB Vector Store hazır!")
    
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
        # 1. Sorguyu vektöre çevir
        query_vector = self.model.encode(query).tolist()
        
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
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        count = collection.count_documents({})
        return count > 0
    except Exception as e:
        print(f"❌ MongoDB bağlantı hatası: {e}")
        return False
