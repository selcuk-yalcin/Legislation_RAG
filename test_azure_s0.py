"""
Azure DI S0 Standard Tier - Large PDF Test
Tests if the upgraded tier can handle 12MB KKD PDF that failed on Free tier
"""

from dotenv import load_dotenv
load_dotenv()

from azure_doc_parser import AzureDocParser
from web_content_fetcher import WebContentFetcher

print("=" * 70)
print("AZURE DI S0 STANDARD - BÜYÜK PDF TEST")
print("=" * 70)

# Initialize
parser = AzureDocParser()
fetcher = WebContentFetcher()

# Test URL: 12MB KKD Kitabı (previously failed with 4MB limit)
test_url = "https://kkdportal.csgb.gov.tr/media/ewedafie/kkd_kitabi.pdf"
print(f"\n📥 Test URL: {test_url}")
print("   (12MB PDF - Free tier'da 4MB limitinde başarısız olmuştu)")

# Step 1: Download
print(f"\n{'=' * 70}")
print("ADIM 1: PDF İNDİRME")
print("=" * 70)
raw_bytes, content_type = fetcher.fetch_raw_bytes(test_url)

if not raw_bytes:
    print("❌ İndirme başarısız - test sonlandırılıyor")
    exit(1)

print(f"✅ İndirildi: {len(raw_bytes):,} bytes ({len(raw_bytes)/1024/1024:.1f} MB)")

# Step 2: Parse with Azure DI
print(f"\n{'=' * 70}")
print("ADIM 2: AZURE DI PARSE (S0 Standard - No Size Limit)")
print("=" * 70)
print("   Model: prebuilt-layout")
print("   Output: markdown (tablolar korunacak)")

markdown = parser.parse_pdf_bytes(raw_bytes)

if not markdown:
    print("❌ Azure DI parse başarısız")
    exit(1)

if len(markdown) < 1000:
    print(f"⚠️  Parse edildi ama çok az içerik: {len(markdown)} karakter")
    exit(1)

# Step 3: Verify Results
print(f"\n{'=' * 70}")
print("ADIM 3: SONUÇ DOĞRULAMA")
print("=" * 70)
print(f"✅ BAŞARILI! Parse edildi: {len(markdown):,} karakter markdown")

# Check for tables
table_markers = markdown.count("|")
heading_markers = markdown.count("#")
print(f"\n📊 İçerik Analizi:")
print(f"   - Tablo karakteri (|): {table_markers:,}")
print(f"   - Başlık karakteri (#): {heading_markers:,}")

if table_markers > 100:
    print("   ✅ Tablolar başarıyla extract edildi!")
if heading_markers > 50:
    print("   ✅ Başlıklar başarıyla tespit edildi!")

# Sample content
print(f"\n📄 Örnek İçerik (İlk 500 karakter):")
print("-" * 70)
print(markdown[:500])
print("...")

print(f"\n📄 Örnek İçerik (Son 300 karakter):")
print("-" * 70)
print(markdown[-300:])

# Check for specific ISG terms
isg_terms = ["kişisel koruyucu", "iş güvenliği", "risk", "madde", "başlık"]
found_terms = [term for term in isg_terms if term.lower() in markdown.lower()]
print(f"\n🔍 ISG Terim Kontrolü:")
print(f"   Bulunan terimler: {', '.join(found_terms)}")

print("\n" + "=" * 70)
print("✅ TEST TAMAMLANDI - S0 STANDARD BAŞARILI!")
print("=" * 70)
print(f"""
ÖZET:
  - PDF boyutu: {len(raw_bytes)/1024/1024:.1f} MB (Free tier 4MB limitini aşıyor)
  - Parse sonucu: {len(markdown):,} karakter markdown
  - Tablolar: {'✅ Var' if table_markers > 100 else '❌ Yok'}
  - Başlıklar: {'✅ Var' if heading_markers > 50 else '❌ Yok'}
  - Azure DI S0 Standard: ✅ Çalışıyor!
""")
