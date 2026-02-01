#!/bin/bash
# MongoDB Atlas Vector Search Test Script

echo "🧪 MongoDB Vector Search Index Testi"
echo "===================================="
echo ""

# Test 1: MongoDB Bağlantısı
echo "1️⃣ MongoDB bağlantısı test ediliyor..."
python3 -c "
from pymongo import MongoClient
from config import MONGO_URI
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
client.admin.command('ping')
print('   ✅ Bağlantı OK')
client.close()
"

# Test 2: Index Varlığı
echo ""
echo "2️⃣ Vector Search Index kontrol ediliyor..."
python3 -c "
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

try:
    indexes = list(collection.list_search_indexes())
    if indexes:
        for idx in indexes:
            print(f\"   ✅ Index bulundu: {idx.get('name')} - Status: {idx.get('status')}\")
    else:
        print('   ⚠️  Vector Search Index bulunamadı!')
except Exception as e:
    print(f'   ❌ Hata: {e}')
finally:
    client.close()
"

# Test 3: Vector Search Sorgusu
echo ""
echo "3️⃣ Vector Search sorgusu test ediliyor..."
python3 -c "
try:
    from mongodb_vector_store import MongoDBVectorStore
    
    store = MongoDBVectorStore()
    results = store.similarity_search('iş sağlığı ve güvenliği', k=3)
    
    print(f'   ✅ Vector Search çalışıyor! {len(results)} sonuç bulundu')
    print('')
    for i, doc in enumerate(results, 1):
        print(f'   [{i}] Score: {doc.score:.4f}')
        preview = doc.page_content[:80].replace('\n', ' ')
        print(f'       {preview}...')
        print(f'       Kaynak: {doc.metadata.get(\"source_file\", \"N/A\")}')
        print('')
        
except Exception as e:
    print(f'   ❌ Vector Search hatası: {e}')
    print('')
    print('   💡 Olası nedenler:')
    print('      - Index henüz Active durumda değil')
    print('      - Index adı yanlış (vector_index olmalı)')
    print('      - Embedding boyutu uyuşmuyor (384 olmalı)')
"

echo ""
echo "===================================="
echo "✅ Test tamamlandı!"
