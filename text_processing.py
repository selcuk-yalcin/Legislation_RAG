"""
Text preprocessing utilities
"""

import re


def clean_text(text):
    """
    Cleans noisy data from PDF text while preserving important numerical values.
    
    Args:
        text (str): Raw text from PDF
        
    Returns:
        str: Cleaned text
    """
    # Remove page separators
    text = re.sub(r'--- PAGE \d+ ---', '', text)
    
    # Remove standalone numbers (page numbers, IDs)
    text = re.sub(r'^\s*\d{3,6}\s*$', '', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
