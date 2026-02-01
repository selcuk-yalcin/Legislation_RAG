"""
Utility functions for Legislation RAG System
OpenRouter-based utilities for multi-document processing
"""

import os
from typing import List, Dict, Optional
from dotenv import load_dotenv, find_dotenv


def load_env():
    """Load environment variables from .env file"""
    _ = load_dotenv(find_dotenv())


def get_openrouter_api_key() -> str:
    """
    Get OpenRouter API key from environment variables
    
    Returns:
        str: OpenRouter API key
    """
    load_env()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    return api_key


def format_source_citation(source_file: str, source_dir: str, page: int) -> str:
    """
    Format a citation from document metadata
    
    Args:
        source_file: Name of the source PDF file
        source_dir: Directory of the source (KANUN VE YÖNETMELİKLER or TEBLİĞ)
        page: Page number in the document
    
    Returns:
        str: Formatted citation string
    """
    # Clean up long file names
    clean_name = source_file.replace('.pdf', '').strip()
    if len(clean_name) > 50:
        clean_name = clean_name[:47] + "..."
    
    return f"📄 {clean_name} (Sayfa {page + 1}) - {source_dir}"


def extract_document_metadata(chunks: List) -> Dict[str, Dict]:
    """
    Extract statistics and metadata from document chunks
    
    Args:
        chunks: List of document chunks with metadata
    
    Returns:
        dict: Statistics about the documents
    """
    stats = {
        'total_chunks': len(chunks),
        'files': {},
        'directories': {}
    }
    
    for chunk in chunks:
        source_file = chunk.metadata.get('source_file', 'Unknown')
        source_dir = chunk.metadata.get('source_dir', 'Unknown')
        
        # Count chunks per file
        if source_file not in stats['files']:
            stats['files'][source_file] = 0
        stats['files'][source_file] += 1
        
        # Count chunks per directory
        if source_dir not in stats['directories']:
            stats['directories'][source_dir] = 0
        stats['directories'][source_dir] += 1
    
    stats['total_files'] = len(stats['files'])
    stats['total_directories'] = len(stats['directories'])
    
    return stats


def print_document_stats(stats: Dict):
    """
    Print document statistics in a readable format
    
    Args:
        stats: Statistics dictionary from extract_document_metadata
    """
    print("\n" + "=" * 60)
    print("📊 DOCUMENT STATISTICS")
    print("=" * 60)
    print(f"Total Chunks: {stats['total_chunks']}")
    print(f"Total Files: {stats['total_files']}")
    print(f"Total Directories: {stats['total_directories']}")
    
    print("\n📁 By Directory:")
    for dir_name, count in sorted(stats['directories'].items()):
        print(f"  • {dir_name}: {count} chunks")
    
    print("\n📄 Top 10 Files by Chunks:")
    sorted_files = sorted(stats['files'].items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (file_name, count) in enumerate(sorted_files, 1):
        clean_name = file_name[:50] + "..." if len(file_name) > 50 else file_name
        print(f"  {i}. {clean_name}: {count} chunks")
    
    print("=" * 60 + "\n")


def validate_chunk_metadata(chunks: List) -> tuple[bool, List[str]]:
    """
    Validate that all chunks have required metadata
    
    Args:
        chunks: List of document chunks
    
    Returns:
        tuple: (is_valid, list of error messages)
    """
    errors = []
    required_fields = ['source_file', 'source_dir', 'page']
    
    for i, chunk in enumerate(chunks):
        for field in required_fields:
            if field not in chunk.metadata:
                errors.append(f"Chunk {i}: Missing '{field}' in metadata")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def get_unique_sources(chunks: List) -> Dict[str, List[str]]:
    """
    Get unique source files organized by directory
    
    Args:
        chunks: List of document chunks
    
    Returns:
        dict: Directory -> list of unique files
    """
    sources = {}
    
    for chunk in chunks:
        source_file = chunk.metadata.get('source_file', 'Unknown')
        source_dir = chunk.metadata.get('source_dir', 'Unknown')
        
        if source_dir not in sources:
            sources[source_dir] = set()
        sources[source_dir].add(source_file)
    
    # Convert sets to sorted lists
    return {dir_name: sorted(list(files)) for dir_name, files in sources.items()}


if __name__ == "__main__":
    # Test utilities
    print("Testing utility functions...")
    
    # Test citation formatting
    citation = format_source_citation(
        "İŞ SAĞLIĞI VE GÜVENLİĞİ KANUNU.pdf",
        "KANUN VE YÖNETMELİKLER",
        5
    )
    print(f"\nSample citation:\n{citation}")
    
    print("\n✅ Utility functions ready!")
