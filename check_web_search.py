from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient
import os

client = MongoClient(os.getenv("MONGO_URI"))
db = client["mevzuat_db"]

# Check web_search collection
count = db.web_search.count_documents({})
print(f"web_search collection: {count} docs")

if count > 0:
    # Get first doc
    doc = db.web_search.find_one({}, {"metadata": 1, "content": 1})
    print(f"\nSample document:")
    print(f"  URL: {doc['metadata']['source_url']}")
    print(f"  Title: {doc['metadata']['document_title']}")
    print(f"  Content: {doc['content'][:300]}...")
    
    # Test search with terms from this doc
    test_query = "iş sağlığı ve güvenliği araştırma"
    print(f"\n🧪 Test query: '{test_query}'")
    print("   (matches web_search doc content)")
    
    from mongodb_vector_store import MongoDBVectorStore
    store = MongoDBVectorStore()
    results = store.similarity_search(test_query, k=5, search_web=True)
    
    print(f"\n📊 Hybrid search results: {len(results)}")
    for i, r in enumerate(results[:3], 1):
        st = r.metadata.get('source_type', 'manual')
        title = r.metadata.get('document_title', 'No title')[:50]
        score = getattr(r, 'score', 0)
        print(f"  {i}. [{st:10s}] {score:.4f} | {title}")
else:
    print("  ❌ No documents in web_search - run test_web_pipeline.py first")
