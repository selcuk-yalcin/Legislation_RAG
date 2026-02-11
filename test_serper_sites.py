"""
Test Serper search across different ISG-related queries
to see which sites it returns
"""
from dotenv import load_dotenv
load_dotenv()

from web_search import SerperWebSearch

def test_serper_sites():
    """Test which sites Serper returns for various ISG queries"""
    
    print("=" * 80)
    print("SERPER SITE COVERAGE TEST - ISG Queries")
    print("=" * 80)
    
    search = SerperWebSearch()
    
    # Different query types
    test_queries = [
        # Kanun/Yönetmelik
        "6331 sayılı iş sağlığı ve güvenliği kanunu",
        "yapı işlerinde isg yönetmeliği",
        "kimyasal maddelerle çalışmalarda sağlık ve güvenlik önlemleri",
        
        # Teknik Rehber
        "yüksekte çalışma isg rehberi",
        "elektrik iş güvenliği",
        "kişisel koruyucu donanım seçimi",
        
        # Güncel Değişiklik
        "2025 isg yönetmelik değişiklikleri",
        "asansör periyodik kontrol süresi",
        
        # Spesifik Terim
        "exproof elektrik sistemleri",
        "isg kurulu toplantı sıklığı",
        "risk değerlendirmesi nasıl yapılır"
    ]
    
    site_stats = {}
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"🔍 Query: {query}")
        print(f"{'='*80}")
        
        results = search.search(query, max_results=5, expand_synonyms=True)
        
        if not results:
            print("   ❌ No results")
            continue
            
        print(f"   ✅ Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            url = result['link']
            title = result['title'][:80]
            
            # Extract domain
            domain = url.split('/')[2] if len(url.split('/')) > 2 else url
            
            # Count domain frequency
            site_stats[domain] = site_stats.get(domain, 0) + 1
            
            print(f"   {i}. [{domain}]")
            print(f"      {title}")
            print(f"      {url[:100]}...")
            
            # Check if obsolete
            if result.get('is_obsolete'):
                print(f"      ⚠️  POTENTIALLY OBSOLETE: {result.get('obsolete_reason')}")
            
            print()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SITE STATISTICS")
    print("=" * 80)
    
    # Sort by frequency
    sorted_sites = sorted(site_stats.items(), key=lambda x: x[1], reverse=True)
    
    for domain, count in sorted_sites:
        percentage = (count / sum(site_stats.values())) * 100
        bar = "█" * int(percentage / 2)
        print(f"  {domain:40s} | {count:3d} ({percentage:5.1f}%) {bar}")
    
    print(f"\n  Total results: {sum(site_stats.values())}")
    print(f"  Unique domains: {len(site_stats)}")
    
    # Check for key sites
    print("\n" + "=" * 80)
    print("🎯 KEY SITE PRESENCE")
    print("=" * 80)
    
    key_sites = {
        "www.mevzuat.gov.tr": "Resmi Mevzuat Portalı",
        "www.resmigazete.gov.tr": "Resmi Gazete",
        "resmigazete.gov.tr": "Resmi Gazete (alt domain)",
        "www.csgb.gov.tr": "ÇSGB Ana Site",
        "kkdportal.csgb.gov.tr": "KKD Portal",
        "guvenliinsaat.csgb.gov.tr": "Güvenli İnşaat",
        "isekipmanlari.csgb.gov.tr": "İş Ekipmanları",
    }
    
    for site, name in key_sites.items():
        count = site_stats.get(site, 0)
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {name:30s} ({site:35s}): {count} results")

if __name__ == "__main__":
    test_serper_sites()
