"""
Legal Document Chunking Utilities
Specialized chunking for Turkish legal documents (KANUN, YÖNETMELİK, TEBLİĞ)
"""

import re
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain.schema import Document
else:
    try:
        from langchain.schema import Document
    except ImportError:
        from langchain_core.documents import Document


def extract_madde_number(text: str) -> str:
    """
    Extracts the article (MADDE) number from text.
    
    Args:
        text (str): Text to search for MADDE number
        
    Returns:
        str: MADDE number or "Unknown"
    """
    # Pattern: "MADDE 12", "Madde 12", "Madde-12", "Madde:12"
    patterns = [
        r"MADDE\s*[:\-–]?\s*(\d+)",
        r"Madde\s*[:\-–]?\s*(\d+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "Unknown"


def extract_bent_letters(text: str) -> List[str]:
    """
    Extracts bent (clause) letters from text.
    
    Args:
        text (str): Text to search for bent letters
        
    Returns:
        List[str]: List of bent letters found (a, b, c, ç, etc.)
    """
    # Pattern: "a) ", "b) ", "ç) ", etc.
    pattern = r"\n([a-zçğıöşü])\)\s"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return matches


def extract_fikra_numbers(text: str) -> List[str]:
    """
    Extracts fıkra (paragraph) numbers from text.
    
    Args:
        text (str): Text to search for fıkra numbers
        
    Returns:
        List[str]: List of fıkra numbers found (1, 2, 3, etc.)
    """
    # Pattern: "(1) ", "(2) ", etc.
    pattern = r"\((\d+)\)\s"
    matches = re.findall(pattern, text)
    return matches


def enrich_chunk_metadata(chunk: Document) -> Document:
    """
    Enriches a document chunk with legal structure metadata.
    
    Args:
        chunk (Document): Original chunk
        
    Returns:
        Document: Chunk with enriched metadata
    """
    text = chunk.page_content
    
    # Extract structural information
    madde_number = extract_madde_number(text)
    bent_letters = extract_bent_letters(text)
    fikra_numbers = extract_fikra_numbers(text)
    
    # Add legal structure metadata
    chunk.metadata['madde_number'] = madde_number
    chunk.metadata['has_bent'] = len(bent_letters) > 0
    chunk.metadata['bent_count'] = len(bent_letters)
    chunk.metadata['has_fikra'] = len(fikra_numbers) > 0
    chunk.metadata['fikra_count'] = len(fikra_numbers)
    
    # Create a human-readable source identifier
    # Example: "İş Güvenliği Uzmanlarının Görev, Yetki, Sorumluluk ve Eğitimleri Hakkında Yönetmelik - MADDE 12"
    document_title = chunk.metadata.get('document_title', 'Unknown Document')
    if madde_number != "Unknown":
        chunk.metadata['full_reference'] = f"{document_title} - MADDE {madde_number}"
        chunk.metadata['is_complete_madde'] = True
    else:
        chunk.metadata['full_reference'] = document_title
        chunk.metadata['is_complete_madde'] = False
    
    return chunk


def post_process_chunks(chunks: List[Document]) -> List[Document]:
    """
    Post-processes chunks to add legal structure metadata.
    
    Args:
        chunks (List[Document]): Original chunks
        
    Returns:
        List[Document]: Chunks with enriched metadata
    """
    print("\n🔍 Analyzing legal structure in chunks...")
    
    enriched_chunks = []
    complete_madde_count = 0
    
    for i, chunk in enumerate(chunks):
        enriched = enrich_chunk_metadata(chunk)
        enriched_chunks.append(enriched)
        
        if enriched.metadata.get('is_complete_madde', False):
            complete_madde_count += 1
    
    print(f"✅ Enriched {len(enriched_chunks)} chunks with legal metadata")
    print(f"   📊 Complete MADDE chunks: {complete_madde_count}/{len(chunks)} ({100*complete_madde_count//len(chunks)}%)")
    
    return enriched_chunks


def analyze_chunk_quality(chunks: List[Document]) -> Dict[str, Any]:
    """
    Analyzes the quality of legal document chunking.
    
    Args:
        chunks (List[Document]): Chunks to analyze
        
    Returns:
        Dict: Quality metrics
    """
    total = len(chunks)
    complete_madde = sum(1 for c in chunks if c.metadata.get('is_complete_madde', False))
    with_bent = sum(1 for c in chunks if c.metadata.get('has_bent', False))
    with_fikra = sum(1 for c in chunks if c.metadata.get('has_fikra', False))
    
    avg_length = sum(len(c.page_content) for c in chunks) / total if total > 0 else 0
    
    return {
        'total_chunks': total,
        'complete_madde_chunks': complete_madde,
        'complete_madde_percentage': (complete_madde / total * 100) if total > 0 else 0,
        'chunks_with_bent': with_bent,
        'chunks_with_fikra': with_fikra,
        'average_chunk_length': avg_length
    }
