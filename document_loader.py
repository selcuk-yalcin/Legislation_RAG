"""
Document loading and processing
Loads ALL PDF files from data directories
AND CREATES EMBEDDINGS for MongoDB Vector Search
"""

import os
import glob
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from text_processing import clean_text
from config import KANUN_DIR, TEBLIG_DIR, CHUNK_SIZE, CHUNK_OVERLAP, MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME, EMBEDDING_MODEL

# Initialize embedding model (will download from HuggingFace if needed)
print("🤖 Loading embedding model...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
print(f"✅ Embedding model loaded: {EMBEDDING_MODEL}")


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
    
    # Add source metadata
    for doc in documents:
        doc.metadata['source_file'] = os.path.basename(pdf_path)
        doc.metadata['source_dir'] = os.path.basename(os.path.dirname(pdf_path))
    
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
        print("\n🧠 Creating embeddings for chunks...")
        documents_to_insert = []
        
        # Process in batches for efficiency
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [chunk.page_content for chunk in batch]
            
            # Generate embeddings for batch
            embeddings = embedding_model.encode(texts, show_progress_bar=True)
            
            for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                doc = {
                    "chunk_id": i + j,
                    "content": chunk.page_content,
                    "metadata": chunk.metadata,
                    "embedding": embedding.tolist(),  # ⭐ VECTOR EKLENDI!
                    "created_at": datetime.utcnow()
                }
                documents_to_insert.append(doc)
            
            print(f"  ✓ Processed {min(i+batch_size, len(chunks))}/{len(chunks)} chunks")
        
        # Insert new documents
        result = collection.insert_many(documents_to_insert)
        print(f"\n✅ Saved {len(result.inserted_ids)} chunks WITH EMBEDDINGS to MongoDB")
        
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
    
    # Split into chunks
    print("\n✂️  Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(all_documents)
    print(f"✅ Created {len(chunks)} chunks")
    
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
