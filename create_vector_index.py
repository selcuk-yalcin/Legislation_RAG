"""
MongoDB Atlas Vector Search Index Oluşturma Script'i

Bu script MongoDB Atlas'ta vector search index oluşturur.
NOT: Atlas UI üzerinden manuel olarak da oluşturulabilir.
"""

from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME, MONGO_VECTOR_INDEX_NAME

def create_vector_search_index():
    """MongoDB Atlas Vector Search Index oluştur"""
    
    print("🔌 MongoDB Atlas'a bağlanılıyor...")
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION_NAME]
    
    # Mevcut index'leri kontrol et
    print("\n📋 Mevcut index'ler kontrol ediliyor...")
    existing_indexes = list(collection.list_search_indexes())
    
    index_exists = any(idx.get('name') == MONGO_VECTOR_INDEX_NAME for idx in existing_indexes)
    
    if index_exists:
        print(f"✅ Vector Search Index zaten mevcut: {MONGO_VECTOR_INDEX_NAME}")
        print("\n📊 Index detayları:")
        for idx in existing_indexes:
            if idx.get('name') == MONGO_VECTOR_INDEX_NAME:
                print(f"  Name: {idx.get('name')}")
                print(f"  Type: {idx.get('type')}")
                print(f"  Status: {idx.get('status')}")
        return
    
    print(f"\n🔧 Vector Search Index oluşturuluyor: {MONGO_VECTOR_INDEX_NAME}")
    
    # Vector Search Index tanımı
    index_definition = {
        "name": MONGO_VECTOR_INDEX_NAME,
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": 384,  # paraphrase-multilingual-MiniLM-L12-v2 = 384 dim
                    "similarity": "cosine"
                },
                {
                    "type": "filter",
                    "path": "metadata.source_file"
                },
                {
                    "type": "filter", 
                    "path": "metadata.source_dir"
                },
                {
                    "type": "filter",
                    "path": "metadata.page"
                }
            ]
        }
    }
    
    try:
        # Atlas Search Index API kullanarak oluştur
        result = collection.create_search_index(index_definition)
        print(f"✅ Index oluşturuldu: {result}")
        print("\n⏳ Index'in aktif hale gelmesi 1-2 dakika sürebilir.")
        print("   Atlas UI'dan kontrol edebilirsiniz:")
        print(f"   https://cloud.mongodb.com → {MONGO_DB_NAME} → Search Indexes")
        
    except Exception as e:
        print(f"\n❌ Index oluşturma hatası: {e}")
        print("\n📝 Manuel oluşturma talimatları:")
        print("1. MongoDB Atlas UI'a gidin")
        print(f"2. Database: {MONGO_DB_NAME} → Collection: {MONGO_COLLECTION_NAME}")
        print("3. 'Search Indexes' sekmesine tıklayın")
        print("4. 'Create Index' → 'JSON Editor' seçin")
        print("5. Aşağıdaki JSON'u yapıştırın:\n")
        
        import json
        print(json.dumps(index_definition, indent=2))
        
    finally:
        client.close()


def verify_vector_search():
    """Vector Search'ün çalışıp çalışmadığını test et"""
    print("\n\n🧪 Vector Search testi yapılıyor...")
    
    try:
        from mongodb_vector_store import MongoDBVectorStore
        
        store = MongoDBVectorStore()
        
        # Test sorgusu
        test_query = "iş sağlığı ve güvenliği"
        print(f"\n🔍 Test sorgusu: '{test_query}'")
        
        results = store.similarity_search(test_query, k=3)
        
        print(f"\n✅ Vector Search çalışıyor! {len(results)} sonuç bulundu:")
        for i, doc in enumerate(results, 1):
            content_preview = doc.page_content[:100].replace('\n', ' ')
            print(f"\n[{i}] Score: {doc.score:.4f}")
            print(f"    Content: {content_preview}...")
            print(f"    Source: {doc.metadata.get('source_file', 'N/A')}")
            
    except Exception as e:
        print(f"\n❌ Vector Search test hatası: {e}")
        print("\n💡 Olası nedenler:")
        print("  1. Index henüz aktif değil (1-2 dakika bekleyin)")
        print("  2. Index tanımı yanlış")
        print("  3. MongoDB bağlantı problemi")


if __name__ == "__main__":
    print("=" * 60)
    print("MongoDB Atlas Vector Search Index Kurulumu")
    print("=" * 60)
    
    create_vector_search_index()
    
    # Test yap
    verify_vector_search()
    
    print("\n" + "=" * 60)
    print("✅ İşlem tamamlandı!")
    print("=" * 60)
