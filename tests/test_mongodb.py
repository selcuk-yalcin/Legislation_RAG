"""
MongoDB Atlas Test Script
Chroma yerine MongoDB Vector Store kullanımını test eder.
"""

from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME
import json

def test_mongodb_connection():
    """MongoDB bağlantısını ve veriyi test et"""
    
    print("=" * 70)
    print("MongoDB Atlas Entegrasyon Testi")
    print("=" * 70)
    
    try:
        print("\n🔌 MongoDB Atlas'a bağlanılıyor...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Ping test
        client.admin.command('ping')
        print("✅ Bağlantı başarılı!")
        
        # Database ve collection
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # İstatistikler
        print(f"\n📊 Database: {MONGO_DB_NAME}")
        print(f"📊 Collection: {MONGO_COLLECTION_NAME}")
        
        total_docs = collection.count_documents({})
        print(f"📊 Toplam döküman: {total_docs:,}")
        
        # Sample döküman
        sample = collection.find_one()
        if sample:
            print(f"\n📄 Örnek Döküman:")
            print(f"  ✓ Content preview: {sample['content'][:100]}...")
            print(f"  ✓ Embedding boyutu: {len(sample['embedding'])} dimensions")
            print(f"  ✓ Metadata:")
            for key, value in sample['metadata'].items():
                if isinstance(value, str) and len(value) > 50:
                    print(f"      - {key}: {value[:50]}...")
                else:
                    print(f"      - {key}: {value}")
        
        # Index'leri listele
        print(f"\n🔍 Mevcut Index'ler:")
        indexes = list(collection.list_indexes())
        for idx in indexes:
            print(f"  - {idx['name']}: {idx.get('key', {})}")
        
        # Search Index'leri kontrol et (Atlas özelliği)
        print(f"\n🔍 Vector Search Index'leri:")
        try:
            search_indexes = list(collection.list_search_indexes())
            if search_indexes:
                for idx in search_indexes:
                    print(f"  ✅ {idx.get('name')}: {idx.get('status', 'N/A')}")
                    print(f"      Type: {idx.get('type')}")
            else:
                print("  ⚠️  Vector Search Index bulunamadı!")
                print("      MONGODB_VECTOR_INDEX_SETUP.md dosyasındaki adımları takip edin.")
        except Exception as e:
            print(f"  ⚠️  Search Index kontrolü başarısız: {e}")
            print("      Not: Bu özellik sadece MongoDB Atlas'ta mevcuttur.")
        
        # Embedding veri tipi kontrolü
        print(f"\n🧪 Embedding Veri Tipi Kontrolü:")
        sample_embedding = sample.get('embedding')
        if sample_embedding:
            print(f"  ✓ Tip: {type(sample_embedding)}")
            print(f"  ✓ Uzunluk: {len(sample_embedding)}")
            print(f"  ✓ İlk 5 değer: {sample_embedding[:5]}")
            
            # Tüm embedding'lerin aynı boyutta olup olmadığını kontrol et
            different_sizes = collection.aggregate([
                {
                    "$project": {
                        "embedding_size": {"$size": "$embedding"}
                    }
                },
                {
                    "$group": {
                        "_id": "$embedding_size",
                        "count": {"$sum": 1}
                    }
                }
            ])
            
            print(f"\n📏 Embedding Boyut Dağılımı:")
            for size_info in different_sizes:
                print(f"  - {size_info['_id']} boyutunda: {size_info['count']} döküman")
        
        print("\n" + "=" * 70)
        print("✅ MongoDB Entegrasyonu Hazır!")
        print("=" * 70)
        
        print("\n📋 Sonraki Adımlar:")
        print("  1. MongoDB Atlas'ta Vector Search Index oluşturun")
        print("     → MONGODB_VECTOR_INDEX_SETUP.md dosyasına bakın")
        print("  2. Index aktif olunca API'yi test edin:")
        print("     → python3 simple_server.py")
        print("  3. Railway'e deploy edin")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        return False
    
    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    test_mongodb_connection()
