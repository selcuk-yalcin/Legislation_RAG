"""
Preprocessing Script - MongoDB Data Ingestion
Processes PDF files and uploads to MongoDB Atlas with embeddings
"""

import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from sentence_transformers import SentenceTransformer
from document_loader import load_and_process_documents
from config import (
    MONGO_URI,
    MONGO_DB_NAME,
    MONGO_COLLECTION_NAME,
    EMBEDDING_MODEL,
    MODEL_CACHE_DIR
)


def main():
    print("=" * 70)
    print("🚀 MongoDB Preprocessing - PDF Dökümanları Yükleme")
    print("=" * 70)
    
    # 1. MongoDB Bağlantısı
    print("\n1️⃣ MongoDB'ye bağlanılıyor...")
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    client.admin.command('ping')
    print("   ✅ Bağlantı başarılı!")
    
    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION_NAME]
    
    # 2. Mevcut veri kontrolü
    existing_count = collection.count_documents({})
    if existing_count > 0:
        print(f"\n⚠️  Koleksiyonda {existing_count} döküman var!")
        # Railway'de otomatik silme (stdin kullanılamaz)
        if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PREPROCESSING_MODE"):
            print("   🔄 Railway mode: Mevcut veriler silinecek...")
            collection.delete_many({})
            print("   ✅ Koleksiyon temizlendi")
        else:
            # Yerel makinede sor
            response = input("   Silmek istiyor musunuz? (y/n): ")
            if response.lower() == 'y':
                collection.delete_many({})
                print("   ✅ Koleksiyon temizlendi")
            else:
                print("   ℹ️  Mevcut verilerin üzerine eklenecek")
    
    # 3. Embedding Modelini Yükle
    print("\n2️⃣ Embedding modeli yükleniyor...")
    os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    
    model = SentenceTransformer(
        EMBEDDING_MODEL,
        cache_folder=MODEL_CACHE_DIR
    )
    
    # Modeli kaydet (Railway'de kullanılacak)
    model_save_path = os.path.join(MODEL_CACHE_DIR, "embedding_model")
    model.save(model_save_path)
    print(f"   ✅ Model kaydedildi: {model_save_path}")
    
    # 4. Dökümanları Yükle ve İşle
    print("\n3️⃣ PDF dökümanları yükleniyor...")
    chunks = load_and_process_documents()
    
    if not chunks:
        print("❌ Hiç döküman bulunamadı!")
        return
    
    print(f"   ✅ {len(chunks)} chunk hazır")
    
    # 5. Embedding Oluştur ve MongoDB'ye Yükle
    print("\n4️⃣ Embeddingleryoluşturuluyor ve MongoDB'ye yükleniyor...")
    print(f"   (Bu işlem ~{len(chunks) * 0.1:.0f} saniye sürebilir)")
    
    documents_to_insert = []
    batch_size = 100
    
    for i, chunk in enumerate(chunks):
        if i % 100 == 0:
            print(f"   İlerleme: {i}/{len(chunks)} ({i*100//len(chunks)}%)")
        
        # Embedding oluştur
        embedding = model.encode(chunk.page_content).tolist()
        
        # MongoDB dökümanı hazırla
        doc = {
            "content": chunk.page_content,
            "embedding": embedding,
            "metadata": chunk.metadata
        }
        
        documents_to_insert.append(doc)
        
        # Batch insert (her 100 dökümanda bir)
        if len(documents_to_insert) >= batch_size:
            collection.insert_many(documents_to_insert)
            documents_to_insert = []
    
    # Kalan dökümanları ekle
    if documents_to_insert:
        collection.insert_many(documents_to_insert)
    
    print(f"   ✅ Tüm dökümanlar yüklendi!")
    
    # 6. İstatistikler
    final_count = collection.count_documents({})
    print("\n" + "=" * 70)
    print("✅ İŞLEM TAMAMLANDI!")
    print("=" * 70)
    print(f"📊 Toplam Döküman: {final_count}")
    print(f"🗄️  Database: {MONGO_DB_NAME}")
    print(f"📦 Collection: {MONGO_COLLECTION_NAME}")
    
    # Örnek döküman
    sample = collection.find_one()
    if sample:
        print(f"\n📄 Örnek Döküman:")
        print(f"   Content uzunluğu: {len(sample['content'])} karakter")
        print(f"   Embedding boyutu: {len(sample['embedding'])} dimension")
        print(f"   Metadata: {sample['metadata']}")
    
    # 7. Atlas Search Index Talimatları
    print("\n" + "=" * 70)
    print("📋 SONRAKİ ADIM: MongoDB Atlas'ta Vector Search Index Oluştur")
    print("=" * 70)
    print("\n1. MongoDB Atlas → Database → Search sekmesine git")
    print("2. 'Create Search Index' → 'JSON Editor' seç")
    print(f"3. Database: {MONGO_DB_NAME}, Collection: {MONGO_COLLECTION_NAME}")
    print("4. Index Name: vector_index")
    print("5. Aşağıdaki JSON'u yapıştır:\n")
    
    embedding_dim = len(sample['embedding']) if sample else 384
    print('{')
    print('  "fields": [')
    print('    {')
    print('      "type": "vector",')
    print('      "path": "embedding",')
    print(f'      "numDimensions": {embedding_dim},')
    print('      "similarity": "cosine"')
    print('    },')
    print('    {')
    print('      "type": "filter",')
    print('      "path": "metadata.source_file"')
    print('    }')
    print('  ]')
    print('}')
    print("\n6. 'Create Search Index' butonuna bas")
    print("\n✅ Index oluştuktan sonra Railway'e deploy edebilirsiniz!")
    print("=" * 70)
    
    client.close()


if __name__ == "__main__":
    main()
