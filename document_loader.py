"""
Document loading and processing - ENTERPRISE GRADE
Loads ALL PDF files from data directories
AND CREATES EMBEDDINGS for MongoDB Vector Search
WITH DETERMINISTIC LEGAL STRUCTURE (MADDE-based hard splitting)

🚀 CRITICAL IMPROVEMENTS:
1. ✅ Deterministik MADDE Hard-Split - RecursiveCharacterTextSplitter'a güvenmez
2. ✅ Metadata Inheritance - MADDE numarası chunk'lar arası miras alınır  
3. ✅ Parent-Child Hierarchy - Her chunk parent_article_content içerir
4. ✅ Voyage AI voyage-law-2 - Türk hukuku için optimize edilmiş embeddings
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
from legal_chunker import (
    post_process_chunks, 
    analyze_chunk_quality,
    hard_split_by_madde,  # 🆕 DETERMINISTIK HARD-SPLIT
    Document
)
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
    🆕 ENTERPRISE-GRADE DOCUMENT PROCESSING:
    1. Loads ALL PDF documents from data directories
    2. Cleans text artifacts
    3. HARD-SPLITS by MADDE boundaries (deterministik)
    4. Falls back to RecursiveCharacterTextSplitter for long MADDEs
    5. Enriches with metadata inheritance & parent-child hierarchy
    
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
    
    # 🆕 STEP 1: DETERMINISTIK HARD-SPLIT BY MADDE
    print("\n🔪 STEP 1: Deterministik MADDE Hard-Split...")
    print("   📋 Splitting documents at MADDE boundaries (not character limits)")
    
    hard_split_chunks = []
    for doc in all_documents:
        # Her dökümanı MADDE sınırlarından böl
        madde_chunks = hard_split_by_madde(doc.page_content, doc.metadata)
        hard_split_chunks.extend(madde_chunks)
    
    print(f"✅ Created {len(hard_split_chunks)} MADDE-level parent chunks")
    
    # 🆕 STEP 2: SECONDARY SPLIT FOR LONG MADDEs (RecursiveCharacterTextSplitter)
    print("\n✂️  STEP 2: Secondary split for MADDEs longer than {CHUNK_SIZE} chars...")
    print("   📋 Using hierarchical separators for legal documents:")
    print("      1️⃣  Bent/Fıkra (Clause/Paragraph) boundaries")
    print("      2️⃣  Double newlines")
    print("      3️⃣  Single newlines")
    print("      4️⃣  Fallback to character splitting")
    
    final_chunks = []
    long_madde_count = 0
    
    for chunk in hard_split_chunks:
        # Eğer chunk CHUNK_SIZE'dan küçükse, olduğu gibi ekle
        if len(chunk.page_content) <= CHUNK_SIZE:
            final_chunks.append(chunk)
        else:
            # Uzun MADDE'leri ikincil olarak böl (ama MADDE context'ini koru!)
            long_madde_count += 1
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                # BENT/FIKRA seviyesinde bölme (MADDE'yi korur!)
                separators=[
                    # 1. Öncelik: BENT ayraçları
                    "\na) ", "\nb) ", "\nc) ", "\nç) ", "\nd) ", 
                    "\ne) ", "\nf) ", "\ng) ", "\nğ) ", "\nh) ",
                    
                    # 2. Öncelik: Fıkra numaraları
                    "\n(1) ", "\n(2) ", "\n(3) ", "\n(4) ", "\n(5) ",
                    
                    # 3. Öncelik: Paragraf ayraçları
                    "\n\n",
                    
                    # 4. Öncelik: Cümle sonları
                    "\n", ". ",
                    
                    # 5. Son çare: Karakter bazlı
                    " ", ""
                ],
                length_function=len,
                is_separator_regex=False
            )
            
            # Bu MADDE'yi alt parçalara böl
            sub_chunks = text_splitter.split_text(chunk.page_content)
            
            # Her alt parçayı Document'e çevir ve parent metadata'yı koru
            for i, sub_text in enumerate(sub_chunks):
                sub_chunk = Document(
                    page_content=sub_text,
                    metadata=chunk.metadata.copy()
                )
                
                # 🔥 PARENT-CHILD WITH DOCUMENT TITLE
                # Parent content zaten hard_split_by_madde'den "DOCUMENT - MADDE X" formatında geliyor
                # Eğer yoksa (eski data için fallback), burada ekle
                if 'parent_article_content' in chunk.metadata:
                    # Zaten var, olduğu gibi kullan
                    sub_chunk.metadata['parent_article_content'] = chunk.metadata['parent_article_content']
                else:
                    # Yoksa, şimdi ekle
                    document_title = chunk.metadata.get('document_title', 'Unknown Document')
                    madde_num = chunk.metadata.get('madde_number', 'Unknown')
                    full_parent_content = f"{document_title} - MADDE {madde_num}\n\n{chunk.page_content}"
                    sub_chunk.metadata['parent_article_content'] = full_parent_content
                
                sub_chunk.metadata['is_sub_chunk'] = True
                sub_chunk.metadata['sub_chunk_index'] = i
                final_chunks.append(sub_chunk)
    
    if long_madde_count > 0:
        print(f"   ✅ Split {long_madde_count} long MADDEs into {len(final_chunks)} total chunks")
    else:
        print(f"   ✅ No MADDEs exceeded {CHUNK_SIZE} characters")
    
    print(f"✅ Total chunks after secondary split: {len(final_chunks)}")
    
    # 🆕 STEP 3: METADATA INHERITANCE & ENRICHMENT
    print("\n🧬 STEP 3: Metadata Inheritance & Legal Structure Enrichment...")
    chunks = post_process_chunks(final_chunks)
    
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
