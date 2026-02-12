"""
Azure DI Model Verification Test
Checks that prebuilt-layout model is correctly configured
"""

print("=" * 80)
print("🔍 AZURE DI MODEL VERIFICATION")
print("=" * 80)

# Test 1: Config check
print("\n1. Config Check:")
from config import AZURE_DI_MODEL
print(f"   ✅ AZURE_DI_MODEL = '{AZURE_DI_MODEL}'")
assert AZURE_DI_MODEL == "prebuilt-layout", f"Expected 'prebuilt-layout', got '{AZURE_DI_MODEL}'"

# Test 2: AzureDocParser check
print("\n2. AzureDocParser Check:")
from azure_doc_parser import AzureDocParser
parser = AzureDocParser()
print(f"   ✅ Parser model = '{parser.model}'")
assert parser.model == "prebuilt-layout", f"Expected 'prebuilt-layout', got '{parser.model}'"

# Test 3: Upload script check
print("\n3. Upload Script Check:")
from upload_klavuzlar_with_azure import KlavuzUploader
uploader = KlavuzUploader()
print(f"   ✅ Uploader parser model = '{uploader.parser.model}'")
assert uploader.parser.model == "prebuilt-layout", f"Expected 'prebuilt-layout', got '{uploader.parser.model}'"

print("\n" + "=" * 80)
print("✅ ALL CHECKS PASSED - prebuilt-layout is correctly configured!")
print("=" * 80)

print("""
📋 Model Features (prebuilt-layout):
   ✅ Table extraction (with cell boundaries)
   ✅ Figure/image detection
   ✅ Heading structure (H1-H6)
   ✅ Paragraph detection
   ✅ Selection marks (checkboxes)
   ✅ Markdown output format
   ✅ Multi-page support
   ✅ High accuracy OCR

💡 This is the BEST model for legal documents with tables!
""")
