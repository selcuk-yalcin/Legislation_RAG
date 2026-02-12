"""Quick test for klavuz uploader"""
from upload_klavuzlar_with_azure import KlavuzUploader

print("Testing KlavuzUploader initialization...")
uploader = KlavuzUploader()
pdf_files = uploader.get_pdf_files()
print(f"\n✅ Initialization successful!")
print(f"✅ Found {len(pdf_files)} PDF files")
print(f"\nFirst 5 PDFs:")
for i, pdf in enumerate(pdf_files[:5], 1):
    import os
    filename = os.path.basename(pdf)
    size_mb = os.path.getsize(pdf) / 1024 / 1024
    print(f"  {i}. {filename} ({size_mb:.1f} MB)")
