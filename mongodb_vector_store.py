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
    
    def similarity_search(self, query, k=10, filter_dict=None, search_web=True, search_guides=True):
        """
        HYBRID MongoDB Vector Search - Searches THREE collections:
        1. documents (manual uploads - kanun/yönetmelik)
        2. web_search (Serper + Azure DI + Voyage - dynamic web content)
        3. guides (klavuzlar - Azure DI parsed guides)
        
        Args:
            query (str): Arama sorgusu
            k (int): Döndürülecek döküman sayısı
            filter_dict (dict): MongoDB query format metadata filtreleri (opsiyonel)
            search_web (bool): web_search collection'ını da ara (default: True)
            search_guides (bool): guides collection'ını da ara (default: True)
            
        Returns:
            list: Document objelerinin listesi (score'a göre sıralı)
        """
        print(f"\n🔍 HYBRID MongoDB Vector Search başlatılıyor...")
        print(f"   • Query: {query[:50]}...")
        print(f"   • K: {k}")
        print(f"   • Filter: {filter_dict if filter_dict else 'None'}")
        print(f"   • Search web_search: {search_web}")
        print(f"   • Search guides: {search_guides}")
        
        # 1. Sorguyu Voyage AI ile vektöre çevir (bir kez, her iki search için)
        result = self.voyage_client.embed([query], model=self.embedding_model, input_type="query")
        query_vector = result.embeddings[0]
        
        # 2. Helper function - bir collection'da vector search yap
        def _search_in_collection(collection_name, index_name, limit):
            """Vector search in a specific collection"""
            collection = self.db[collection_name]
            
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": index_name,
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": limit * 10,
                        "limit": limit
                    }
                }
            ]
            
            # Metadata filter (if provided)
            if filter_dict:
                pipeline.append({"$match": filter_dict})
            
            # Projection
            pipeline.append({
                "$project": {
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            })
            
            try:
                results = list(collection.aggregate(pipeline))
                return results
            except Exception as e:
                print(f"   ⚠️  {collection_name} search failed: {e}")
                return []
        
        # 3. Search in DOCUMENTS collection (manual uploads)
        print(f"   📚 Searching 'documents' collection...")
        docs_results = _search_in_collection(
            collection_name=MONGO_COLLECTION_NAME,  # "documents"
            index_name=MONGO_VECTOR_INDEX_NAME,      # "vector_index"
            limit=k
        )
        print(f"   ✅ documents: {len(docs_results)} results")
        
        # 4. Search in WEB_SEARCH collection (Serper + Azure DI)
        web_results = []
        if search_web:
            print(f"   🌐 Searching 'web_search' collection...")
            try:
                web_results = _search_in_collection(
                    collection_name="web_search",
                    index_name="web_vector_index",  # ⚠️ INDEX MUST EXIST IN ATLAS
                    limit=k
                )
                print(f"   ✅ web_search: {len(web_results)} results")
            except Exception as e:
                # If index doesn't exist yet, skip web search
                print(f"   ⚠️  web_search skipped (index not ready): {str(e)[:80]}")
                print(f"   💡 Create 'web_vector_index' in MongoDB Atlas to enable web search")
        
        # 5. Search in GUIDES collection (Kılavuzlar - Azure DI parsed)
        guides_results = []
        if search_guides:
            print(f"   📚 Searching 'guides' collection...")
            try:
                guides_results = _search_in_collection(
                    collection_name="guides",
                    index_name="guides_vector_index",  # ⚠️ INDEX MUST EXIST IN ATLAS
                    limit=k
                )
                print(f"   ✅ guides: {len(guides_results)} results")
            except Exception as e:
                # If index doesn't exist yet, skip guides search
                print(f"   ⚠️  guides skipped (index not ready): {str(e)[:80]}")
                print(f"   💡 Run upload_klavuzlar_with_azure.py to populate guides")
        
        # 6. Merge results and sort by score
        all_results = docs_results + web_results + guides_results
        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Take top-k from merged results
        top_results = all_results[:k]
        print(f"   🎯 HYBRID TOTAL: {len(all_results)} merged → {len(top_results)} final")
        
        # 6. Convert to LangChain Document format
        documents = []
        for result in top_results:
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
        """
        Tüm collection'ların istatistiklerini döndür.
        
        Returns:
            dict: Stats for documents, web_search, and guides collections
        """
        stats = {
            "database": MONGO_DB_NAME,
            "documents": {
                "collection": MONGO_COLLECTION_NAME,
                "count": self.collection.count_documents({})
            }
        }
        
        # Web search stats
        try:
            web_collection = self.db["web_search"]
            stats["web_search"] = {
                "collection": "web_search",
                "count": web_collection.count_documents({})
            }
        except Exception:
            stats["web_search"] = {"count": 0, "status": "not_available"}
        
        # Guides stats
        try:
            guides_collection = self.db["guides"]
            stats["guides"] = {
                "collection": "guides",
                "count": guides_collection.count_documents({})
            }
        except Exception:
            stats["guides"] = {"count": 0, "status": "not_available"}
        
        # Total
        total = sum(
            s["count"] for s in [stats["documents"], stats.get("web_search", {}), stats.get("guides", {})]
            if isinstance(s.get("count"), int)
        )
        stats["total_documents"] = total
        
        return stats
    
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
