#!/usr/bin/env python3
"""
Fresh document upload with MADDE-based chunking
"""

from document_loader import load_and_process_documents

if __name__ == "__main__":
    print("🚀 MADDE-bazlı chunking başlıyor...")
    print("=" * 70)
    
    chunks = load_and_process_documents()
    
    print("=" * 70)
    print(f"🎉 TAMAMLANDI! {len(chunks)} chunk MongoDB'ye yüklendi!")
