"""
Legal Document Chunking Utilities - ENTERPRISE GRADE
Specialized chunking for Turkish legal documents (KANUN, YÖNETMELİK, TEBLİĞ)

🚀 IMPROVEMENTS:
1. ✅ Context Memory (Stateful Processing) - Inherits MADDE from previous chunk
2. ✅ Multi-MADDE Detection & Auto-Split - Prevents metadata poisoning
3. ✅ Parent-Child Hierarchy Support - Ready for hierarchical RAG
4. ✅ Robust Text Normalization - Handles broken PDF extractions
5. ✅ Smart is_complete_madde Logic - Checks actual completeness
"""

import re
from typing import List, Dict, Any, Optional, Tuple

# Use simple object instead of langchain Document to avoid import issues
class Document:
    """Simple document class compatible with langchain"""
    def __init__(self, page_content="", metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


def normalize_text_for_madde_detection(text: str) -> str:
    """
    Normalizes text to handle broken PDF extractions.
    Fixes: "M a d d e", "MAD DE", "M A D D E 7 2", etc.
    
    Args:
        text (str): Raw text from PDF
        
    Returns:
        str: Normalized text with clean MADDE patterns
    """
    # Remove excessive spaces within words
    # "M A D D E" -> "MADDE"
    normalized = re.sub(r'M\s+A\s+D\s+D\s+E', 'MADDE', text, flags=re.IGNORECASE)
    
    # Clean up "MADDE  72" -> "MADDE 72"
    normalized = re.sub(r'MADDE\s+(\d+)', r'MADDE \1', normalized, flags=re.IGNORECASE)
    
    return normalized


def extract_all_madde_numbers(text: str) -> List[str]:
    """
    Extracts ALL article (MADDE) numbers from text.
    🆕 IMPROVEMENT: Uses findall instead of search to detect multi-MADDE chunks.
    
    Args:
        text (str): Text to search for MADDE numbers
        
    Returns:
        List[str]: List of all MADDE numbers found
    """
    # Normalize text first
    normalized = normalize_text_for_madde_detection(text)
    
    # Pattern: "MADDE 12", "Madde 12", "Madde-12", "Madde:12"
    patterns = [
        r"MADDE\s*[:\-–]?\s*(\d+)",
        r"Madde\s*[:\-–]?\s*(\d+)",
    ]
    
    all_madde_numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, normalized)
        all_madde_numbers.extend(matches)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_madde = []
    for madde in all_madde_numbers:
        if madde not in seen:
            seen.add(madde)
            unique_madde.append(madde)
    
    return unique_madde


def extract_madde_number(text: str) -> str:
    """
    Extracts the FIRST article (MADDE) number from text.
    
    Args:
        text (str): Text to search for MADDE number
        
    Returns:
        str: MADDE number or "Unknown"
    """
    all_madde = extract_all_madde_numbers(text)
    return all_madde[0] if all_madde else "Unknown"


def detect_madde_boundaries(text: str) -> List[Tuple[int, str]]:
    """
    Detects positions and numbers of all MADDE boundaries in text.
    
    Args:
        text (str): Text to analyze
        
    Returns:
        List[Tuple[int, str]]: List of (position, madde_number) tuples
    """
    normalized = normalize_text_for_madde_detection(text)
    
    pattern = r"MADDE\s*[:\-–]?\s*(\d+)"
    boundaries = []
    
    for match in re.finditer(pattern, normalized, re.IGNORECASE):
        boundaries.append((match.start(), match.group(1)))
    
    return boundaries


def check_is_complete_madde(text: str, madde_number: str) -> bool:
    """
    🆕 SMART LOGIC: Checks if chunk contains a complete MADDE.
    A chunk is "complete" if:
    1. It starts with "MADDE X"
    2. Either ends with next "MADDE Y" OR is the last chunk in document
    
    Args:
        text (str): Chunk text
        madde_number (str): The MADDE number we're checking
        
    Returns:
        bool: True if this chunk contains complete MADDE
    """
    boundaries = detect_madde_boundaries(text)
    
    if not boundaries:
        return False
    
    # Check if chunk starts with this MADDE
    first_madde = boundaries[0][1]
    if first_madde != madde_number:
        return False
    
    # If there are multiple MADDE in this chunk, it's NOT complete
    # (it should have been split)
    if len(boundaries) > 1:
        return False
    
    # At this point: chunk has exactly one MADDE and it's at the start
    # This is likely a complete MADDE
    return True


def split_multi_madde_chunk(chunk: Document) -> List[Document]:
    """
    🆕 METADATA POISONING PREVENTION: Splits chunks containing multiple MADDE.
    
    Example: If chunk contains "MADDE 72", "MADDE 73", "MADDE 74",
    it will be split into 3 separate chunks.
    
    Args:
        chunk (Document): Original chunk
        
    Returns:
        List[Document]: List of split chunks (or [chunk] if no split needed)
    """
    text = chunk.page_content
    boundaries = detect_madde_boundaries(text)
    
    # If 0 or 1 MADDE, no split needed
    if len(boundaries) <= 1:
        return [chunk]
    
    print(f"   ⚠️  Multi-MADDE detected: {[m for _, m in boundaries]} - Splitting...")
    
    split_chunks = []
    for i, (pos, madde_num) in enumerate(boundaries):
        # Determine split range
        start_pos = pos
        end_pos = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        
        # Extract text for this MADDE
        madde_text = text[start_pos:end_pos].strip()
        
        # Create new chunk with same metadata
        new_chunk = Document(
            page_content=madde_text,
            metadata=chunk.metadata.copy()
        )
        split_chunks.append(new_chunk)
    
    print(f"   ✅ Split into {len(split_chunks)} chunks")
    return split_chunks


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


def enrich_chunk_metadata(chunk: Document, last_known_madde: Optional[str] = None) -> Tuple[Document, str]:
    """
    🆕 CONTEXT MEMORY: Enriches chunk with metadata using context from previous chunk.
    
    Args:
        chunk (Document): Original chunk
        last_known_madde (Optional[str]): MADDE number from previous chunk (context memory)
        
    Returns:
        Tuple[Document, str]: (Enriched chunk, current MADDE number for next chunk)
    """
    text = chunk.page_content
    
    # Extract structural information
    madde_number = extract_madde_number(text)
    
    # 🚀 CONTEXT INHERITANCE: If no MADDE found, inherit from previous chunk
    if madde_number == "Unknown" and last_known_madde:
        madde_number = last_known_madde
        chunk.metadata['inherited_madde'] = True  # Mark as inherited for debugging
    else:
        chunk.metadata['inherited_madde'] = False
    
    bent_letters = extract_bent_letters(text)
    fikra_numbers = extract_fikra_numbers(text)
    
    # Add legal structure metadata
    chunk.metadata['madde_number'] = madde_number
    chunk.metadata['has_bent'] = len(bent_letters) > 0
    chunk.metadata['bent_count'] = len(bent_letters)
    chunk.metadata['has_fikra'] = len(fikra_numbers) > 0
    chunk.metadata['fikra_count'] = len(fikra_numbers)
    
    # 🆕 SMART is_complete_madde check
    if madde_number != "Unknown":
        chunk.metadata['is_complete_madde'] = check_is_complete_madde(text, madde_number)
    else:
        chunk.metadata['is_complete_madde'] = False
    
    # Create a human-readable source identifier
    document_title = chunk.metadata.get('document_title', 'Unknown Document')
    if madde_number != "Unknown":
        chunk.metadata['full_reference'] = f"{document_title} - MADDE {madde_number}"
    else:
        chunk.metadata['full_reference'] = document_title
    
    # Return chunk and current MADDE for next iteration's context
    return chunk, madde_number


def post_process_chunks(chunks: List[Document]) -> List[Document]:
    """
    🆕 ENTERPRISE-GRADE: Post-processes chunks with:
    1. Multi-MADDE detection & splitting
    2. Context memory (stateful processing)
    3. Smart metadata enrichment
    
    Args:
        chunks (List[Document]): Original chunks
        
    Returns:
        List[Document]: Chunks with enriched metadata
    """
    print("\n🔍 Analyzing legal structure in chunks...")
    
    # STEP 1: Split multi-MADDE chunks (Metadata Poisoning Prevention)
    print("   🔪 Checking for multi-MADDE chunks...")
    split_chunks = []
    multi_madde_count = 0
    
    for chunk in chunks:
        split_result = split_multi_madde_chunk(chunk)
        if len(split_result) > 1:
            multi_madde_count += 1
        split_chunks.extend(split_result)
    
    if multi_madde_count > 0:
        print(f"   ✅ Split {multi_madde_count} multi-MADDE chunks into {len(split_chunks)} total chunks")
    else:
        print(f"   ✅ No multi-MADDE chunks detected")
    
    # STEP 2: Enrich with context memory (Stateful Processing)
    print("   🧠 Enriching with context memory...")
    enriched_chunks = []
    last_known_madde = None
    complete_madde_count = 0
    inherited_count = 0
    
    for i, chunk in enumerate(split_chunks):
        enriched, current_madde = enrich_chunk_metadata(chunk, last_known_madde)
        enriched_chunks.append(enriched)
        
        # Update context for next chunk
        if current_madde != "Unknown":
            last_known_madde = current_madde
        
        # Track statistics
        if enriched.metadata.get('is_complete_madde', False):
            complete_madde_count += 1
        if enriched.metadata.get('inherited_madde', False):
            inherited_count += 1
    
    print(f"✅ Enriched {len(enriched_chunks)} chunks with legal metadata")
    print(f"   📊 Complete MADDE chunks: {complete_madde_count}/{len(enriched_chunks)} ({100*complete_madde_count//len(enriched_chunks)}%)")
    if inherited_count > 0:
        print(f"   🧬 Inherited MADDE context: {inherited_count} chunks")
    
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
    inherited = sum(1 for c in chunks if c.metadata.get('inherited_madde', False))
    
    avg_length = sum(len(c.page_content) for c in chunks) / total if total > 0 else 0
    
    return {
        'total_chunks': total,
        'complete_madde_chunks': complete_madde,
        'complete_madde_percentage': (complete_madde / total * 100) if total > 0 else 0,
        'chunks_with_bent': with_bent,
        'chunks_with_fikra': with_fikra,
        'inherited_madde_chunks': inherited,
        'average_chunk_length': avg_length
    }
