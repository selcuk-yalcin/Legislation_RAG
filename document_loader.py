"""
Document loading and processing
Loads ALL PDF files from data directories
AND CREATES EMBEDDINGS for MongoDB Vector Search
WITH LEGAL STRUCTURE AWARENESS (MADDE-based chunking)
"""

import os
import glob
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import voyageai
from text_processing import clean_text
from legal_chunker import post_process_chunks, analyze_chunk_quality
from config import (
    KANUN_DIR, 
    TEBLIG_DIR, 
    CHUNK_SIZE, 
    CHUNK_OVERLAP, 
    MONGO_URI, 
    MONGO_DB_NAME, 
    MONGO_COLLECTION_NAME,
    VOYAGE_API_KEY,
    VOYAGE_EMBEDDING_MODEL
)

# Initialize Voyage AI client
print("🤖 Initializing Voyage AI embedding client...")
voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
print(f"✅ Voyage AI client ready: {VOYAGE_EMBEDDING_MODEL}")


def load_single_pdf(pdf_path):
    """
    Loads a single PDF document.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        list: List of document pages
    """
    print(f"  📄 Loading: {os.path.basename(pdf_path)}")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # Extract document title from filename (remove .pdf extension)
    filename = os.path.basename(pdf_path)
    document_title = filename.replace('.pdf', '')
    source_directory = os.path.basename(os.path.dirname(pdf_path))
    
    # Add enriched source metadata
    for doc in documents:
        doc.metadata['source_file'] = filename
        doc.metadata['source_dir'] = source_directory
        doc.metadata['document_title'] = document_title
        doc.metadata['document_type'] = source_directory  # KANUN VE YÖNETMELİKLER or TEBLİĞ
    
    return documents


def load_all_pdfs_from_directory(directory_path):
    """
    Loads all PDF files from a directory.
    
    Args:
        directory_path (str): Path to the directory containing PDF files
        
    Returns:
        list: List of all document pages from all PDFs
    """
    all_documents = []
    
    if not os.path.exists(directory_path):
        print(f"⚠️  Directory not found: {directory_path}")
        return all_documents
    
    # Find all PDF files in the directory
    pdf_files = glob.glob(os.path.join(directory_path, "*.pdf"))
    
    if not pdf_files:
        print(f"⚠️  No PDF files found in: {directory_path}")
        return all_documents
    
    print(f"\n📁 Found {len(pdf_files)} PDF files in {os.path.basename(directory_path)}")
    
    for pdf_path in pdf_files:
        try:
            documents = load_single_pdf(pdf_path)
            all_documents.extend(documents)
        except Exception as e:
            print(f"  ❌ Error loading {os.path.basename(pdf_path)}: {str(e)}")
            continue
    
    return all_documents


def save_chunks_to_mongodb(chunks):
    """
    Saves document chunks WITH EMBEDDINGS to MongoDB.
    
    Args:
        chunks (list): List of document chunks
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("\n💾 Connecting to MongoDB...")
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        # Clear existing documents (optional)
        collection.delete_many({})
        print("🗑️ Cleared existing documents")
        
        # Prepare documents for MongoDB WITH EMBEDDINGS
        print("\n🧠 Creating embeddings with Voyage AI...")
        documents_to_insert = []
        
        # Process in batches for efficiency (Voyage AI supports batch processing)
        batch_size = 128  # Voyage AI optimal batch size
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [chunk.page_content for chunk in batch]
            
            # Generate embeddings using Voyage AI
            print(f"  🌊 Embedding batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}...")
            result = voyage_client.embed(
                texts, 
                model=VOYAGE_EMBEDDING_MODEL,
                input_type="document"
            )
            embeddings = result.embeddings
            
            for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                doc = {
                    "chunk_id": i + j,
                    "content": chunk.page_content,
                    "metadata": chunk.metadata,
                    "embedding": embedding,  # ⭐ VOYAGE AI 1024-DIM VECTOR!
                    "created_at": datetime.utcnow()
                }
                documents_to_insert.append(doc)
            
            print(f"  ✓ Processed {min(i+batch_size, len(chunks))}/{len(chunks)} chunks")
        
        # Insert new documents
        result = collection.insert_many(documents_to_insert)
        print(f"\n✅ Saved {len(result.inserted_ids)} chunks WITH 1024-DIM EMBEDDINGS to MongoDB")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB error: {str(e)}")
        return False


def load_and_process_documents():
    """
    Loads ALL PDF documents from data directories, cleans text, and splits into chunks.
    Each document is processed individually with its own metadata.
    
    Returns:
        list: List of document chunks ready for embedding
    """
    print("\n📚 Loading ALL documents from data directories...")
    
    all_documents = []
    
    # Load from KANUN VE YÖNETMELİKLER directory
    print("\n🏛️  Loading laws and regulations...")
    kanun_docs = load_all_pdfs_from_directory(KANUN_DIR)
    all_documents.extend(kanun_docs)
    
    # Load from TEBLİĞ directory
    print("\n📢 Loading official notifications...")
    teblig_docs = load_all_pdfs_from_directory(TEBLIG_DIR)
    all_documents.extend(teblig_docs)
    
    if not all_documents:
        print("\n❌ No documents loaded from any directory!")
        return []
    
    print(f"\n✅ Total loaded: {len(all_documents)} pages from all documents")
    
    # Clean all documents
    print("\n🧹 Cleaning document artifacts...")
    for doc in all_documents:
        doc.page_content = clean_text(doc.page_content)
    
    print(f"✅ Cleaned {len(all_documents)} pages")
    
    # Split into chunks with LEGAL STRUCTURE AWARENESS
    print("\n✂️  Splitting documents into MADDE-BASED chunks...")
    print("📋 Using hierarchical separators for legal documents:")
    print("   1️⃣  MADDE (Article) boundaries")
    print("   2️⃣  Bent/Fıkra (Clause/Paragraph) boundaries")
    print("   3️⃣  Double newlines")
    print("   4️⃣  Single newlines")
    print("   5️⃣  Fallback to character splitting")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # HUKUKI YAPI FARKINDALIKLI AYRAÇLAR
        separators=[
            # 1. Öncelik: MADDE başlıkları (en önemli!)
            "\nMADDE ",
            "\nMadde ",
            "\nMadde-",
            "\nMadde:",
            "\nMadde–",
            
            # 2. Öncelik: BENT ve FIKRA ayraçları
            "\na) ",
            "\nb) ",
            "\nc) ",
            "\nç) ",
            "\nd) ",
            "\ne) ",
            "\nf) ",
            "\ng) ",
            "\nğ) ",
            "\nh) ",
            
            # 3. Öncelik: Fıkra numaraları
            "\n(1) ",
            "\n(2) ",
            "\n(3) ",
            "\n(4) ",
            "\n(5) ",
            
            # 4. Öncelik: Paragraf ayraçları
            "\n\n",
            
            # 5. Öncelik: Cümle sonları
            "\n",
            ". ",
            
            # 6. Son çare: Karakter bazlı
            " ",
            ""
        ],
        # Madde bütünlüğünü korumak için overlap artırıldı
        length_function=len,
        is_separator_regex=False
    )
    chunks = text_splitter.split_documents(all_documents)
    print(f"✅ Created {len(chunks)} MADDE-AWARE chunks")
    
    # Enrich chunks with legal structure metadata
    chunks = post_process_chunks(chunks)
    
    # Analyze chunk quality
    quality_metrics = analyze_chunk_quality(chunks)
    print("\n📊 Legal Structure Analysis:")
    print(f"   ✅ Complete MADDE chunks: {quality_metrics['complete_madde_chunks']} ({quality_metrics['complete_madde_percentage']:.1f}%)")
    print(f"   📝 Chunks with BENT: {quality_metrics['chunks_with_bent']}")
    print(f"   📝 Chunks with FIKRA: {quality_metrics['chunks_with_fikra']}")
    print(f"   📏 Average chunk length: {quality_metrics['average_chunk_length']:.0f} characters")
    
    # Show statistics
    if chunks:
        print("\n📊 Document Statistics:")
        source_files = set(chunk.metadata.get('source_file', 'Unknown') for chunk in chunks)
        source_dirs = set(chunk.metadata.get('source_dir', 'Unknown') for chunk in chunks)
        print(f"  • Directories: {', '.join(sorted(source_dirs))}")
        print(f"  • Total files processed: {len(source_files)}")
        print(f"  • Total pages: {len(all_documents)}")
        print(f"  • Total chunks: {len(chunks)}")
        print(f"  • Average chunks per file: {len(chunks) // len(source_files)}")
        
        # Save to MongoDB
        save_chunks_to_mongodb(chunks)
    
    return chunks
