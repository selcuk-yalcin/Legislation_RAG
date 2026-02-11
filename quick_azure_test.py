from dotenv import load_dotenv
load_dotenv()

from azure_doc_parser import AzureDocParser  
from web_content_fetcher import WebContentFetcher

parser = AzureDocParser()
fetcher = WebContentFetcher()

# Fast test with small HTML
test_url = 'https://www.csgb.gov.tr/isgum/'
print(f'Testing: {test_url}')

raw_bytes, ct = fetcher.fetch_raw_bytes(test_url)
if raw_bytes:
    md = parser.parse_html_bytes(raw_bytes)
    if md and len(md) > 100:
        print(f'✅ AZURE DI S0 STANDARD WORKS!')
        print(f'   Parsed: {len(md):,} chars')
        print(f'   Tables: {md.count("|"):,} markers')
    else:
        print('❌ Parse failed')
else:
    print('❌ Download failed')
