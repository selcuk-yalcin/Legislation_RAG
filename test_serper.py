"""
Serper Web Search Test Script
Tests the Serper.dev API integration for Turkish legislation search.
"""

import os
from web_search import SerperWebSearch

# Test queries
TEST_QUERIES = [
    "İş Sağlığı ve Güvenliği Kanunu Madde 4",
    "Yapı İşlerinde İSG Yönetmeliği güncel",
    "6331 sayılı kanun değişiklik",
    "asansör bakım yönetmeliği 2025",
    "yüksekte çalışma korkuluk yüksekliği",
    "kimyasalların olduğu alanlarda elektrik sistemlerinin exproof özellikte olması hangi mevzuatta geçiyor",
    "ilkyardımcı sertifikası kaç yıl geçerli"
]


def test_serper():
    """Test Serper.dev search with sample queries"""
    
    # Set API key (for testing)
    os.environ["SERPER_API_KEY"] = "06f0eda33581aa5c10f2b90dec87062cd7ce64e9"
    
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("❌ SERPER_API_KEY not set!")
        print("   Please set it in your .env file or environment")
        return
    
    print("=" * 70)
    print("🧪 SERPER WEB SEARCH TEST")
    print("=" * 70)
    print(f"✅ API Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # Initialize search engine
    try:
        search = SerperWebSearch()
    except Exception as e:
        print(f"❌ Failed to initialize SerperWebSearch: {e}")
        return
    
    # Test each query
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*70}")
        print(f"📝 Test {i}/{len(TEST_QUERIES)}: {query}")
        print("=" * 70)
        
        try:
            results = search.search(query, max_results=3)
            
            if not results:
                print("   ⚠️  No results found")
                continue
            
            print(f"\n   ✅ Found {len(results)} results:\n")
            
            for idx, result in enumerate(results, 1):
                print(f"   [{idx}] {result['title']}")
                print(f"       URL: {result['link']}")
                print(f"       Snippet: {result['snippet'][:100]}...")
                if result.get('date'):
                    print(f"       Date: {result['date']}")
                print()
        
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    test_serper()
