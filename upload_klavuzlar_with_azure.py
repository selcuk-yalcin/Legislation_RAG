"""
Kılavuz Upload Script - Azure DI + Voyage AI + MongoDB
Sonrasında export tool ile 3 yere kopyalanır (MongoDB + Local + Azure)
"""
import os, glob, time, json
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient
import voyageai
from azure_doc_parser import AzureDocParser
from web_doc_chunker import WebDocumentChunker
from config import VOYAGE_API_KEY, VOYAGE_EMBEDDING_MODEL, MONGO_URI, MONGO_DB_NAME

class KlavuzUploader:
    KLAVUZ_DIR = "./data/KLAVUZLAR"
    COLLECTION_NAME = "guides"
    
    def __init__(self):
        print("=" * 80)
        print("📚 KLAVUZ UPLOADER - Azure DI + Voyage AI + MongoDB")
        print("=" * 80)
        self.parser = AzureDocParser()
        self.chunker = WebDocumentChunker(max_chunk_size=1500, min_chunk_size=100, overlap=200)
        self.voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
        self.mongo_client = MongoClient(MONGO_URI)
        self.collection = self.mongo_client[MONGO_DB_NAME][self.COLLECTION_NAME]
        print(f"✅ Ready | Existing: {self.collection.count_documents({})} chunks\n")
        self.stats = {"total_pdfs": 0, "processed": 0, "failed": 0, "total_chunks": 0, "skipped": 0}
    
    def batch_embed(self, texts, batch_size=50):
        """Embed texts in batches to avoid Voyage AI token limit (120k tokens)"""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            result = self.voyage_client.embed(batch, model=VOYAGE_EMBEDDING_MODEL, input_type="document")
            all_embeddings.extend(result.embeddings)
            if len(texts) > batch_size:
                print(f"      └─ Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        return all_embeddings
    
    def process_pdf(self, pdf_path):
        filename = os.path.basename(pdf_path)
        if self.collection.find_one({"metadata.source_file": filename}):
            print(f"⏭️  Skip: {filename}")
            self.stats["skipped"] += 1
            return
        
        print(f"📄 {filename} ({os.path.getsize(pdf_path)/1024/1024:.1f} MB)")
        start = time.time()
        try:
            md = self.parser.parse_pdf(pdf_path)
            if not md or len(md) < 100:
                raise ValueError("Empty content")
            
            title = Path(filename).stem.replace("-", " ").title()
            chunks = self.chunker.chunk_document(md, f"file://{pdf_path}", title, "markdown")
            
            texts = [c["content"] for c in chunks]
            embs = self.batch_embed(texts)  # Use batched embedding
            
            docs = [{
                "content": c["content"],
                "embedding": e,
                "metadata": {**c["metadata"], "source_file": filename, "guide_title": title,
                           "collection_type": "guide", "chunk_index": i, "total_chunks": len(chunks),
                           "processed_at": datetime.now()}
            } for i, (c, e) in enumerate(zip(chunks, embs))]
            
            self.collection.insert_many(docs)
            print(f"✅ {len(docs)} chunks | {time.time()-start:.1f}s\n")
            self.stats["processed"] += 1
            self.stats["total_chunks"] += len(docs)
        except Exception as e:
            print(f"❌ Error: {e}\n")
            self.stats["failed"] += 1
    
    def run(self):
        pdfs = sorted(glob.glob(os.path.join(self.KLAVUZ_DIR, "*.pdf")))
        self.stats["total_pdfs"] = len(pdfs)
        print(f"🚀 Starting: {len(pdfs)} PDFs\n")
        
        for i, pdf in enumerate(pdfs, 1):
            print(f"[{i}/{len(pdfs)}] ", end="")
            self.process_pdf(pdf)
        
        print("=" * 80)
        print(f"✅ COMPLETE | Processed: {self.stats['processed']} | Failed: {self.stats['failed']} | Skipped: {self.stats['skipped']}")
        print(f"📊 Total chunks: {self.stats['total_chunks']} | DB now has: {self.collection.count_documents({}):,} chunks")
        print("=" * 80)

if __name__ == "__main__":
    resp = input("🤔 Upload 75 klavuz PDFs to MongoDB? (y/n): ").strip().lower()
    if resp == 'y':
        uploader = KlavuzUploader()
        uploader.run()
        print("\n💡 Next: Run 'python export_guides.py' to export to Local + Azure")
    else:
        print("❌ Cancelled")
