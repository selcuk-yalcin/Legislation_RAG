"""
Query Relevance Filter
Detects if a user query is actually related to Turkish labor law and ISG.
Prevents wasting API calls on irrelevant questions (space travel, cooking, etc.)
"""

import re
from typing import Tuple


class QueryRelevanceFilter:
    """
    Fast pre-filter to detect if query is related to ISG/labor law.
    Uses keyword matching + domain detection.
    """
    
    # ISG-related keywords (weighted)
    ISG_KEYWORDS = {
        # High confidence (3 points)
        "iş sağlığı", "isg", "iş güvenliği", "meslek hastalığı", "iş kazası",
        "risk değerlendirmesi", "kkd", "kişisel koruyucu", "işveren", "çalışan",
        "6331", "resmi gazete", "yönetmelik", "kanun", "mevzuat", "madde",
        
        # Medium confidence (2 points)  
        "işyeri", "işçi", "işveren yükümlülüğü", "güvenlik", "sağlık",
        "koruyucu donanım", "acil durum", "yangın", "ilk yardım", "eğitim",
        "bakanlık", "çalışma", "sosyal güvenlik", "sgk", "teftis",
        
        # Low confidence (1 point)
        "iş", "çalışma", "risk", "tehlike", "kontrol", "önlem", "rapor",
        "bildirim", "belge", "yetkili", "sorumlu", "zimmet", "ceza"
    }
    
    # Negative keywords (immediate reject)
    # Note: Use specific phrases to avoid false positives
    IRRELEVANT_KEYWORDS = {
        "uzay istasyonu", "ay'a seyahat", "mars", "gezegen", "asteroid", "galaksi",
        "yemek tarif", "yemek pişir", "malzeme", "fırın",
        "futbol maç", "basketbol", "skor",
        "film izle", "dizi", "müzik dinle", "sanatçı",
        "bitcoin", "kripto para", "hisse senedi",
        "otel", "tatil", "plaj"
    }
    
    def __init__(self, min_score: float = 1.0):
        """
        Args:
            min_score: Minimum relevance score (0-10 scale)
                      1.0 = very permissive
                      3.0 = moderate
                      5.0 = strict
        """
        self.min_score = min_score
        print(f"✅ Query Relevance Filter initialized (min_score={min_score})")
    
    def is_relevant(self, query: str) -> Tuple[bool, float, str]:
        """
        Check if query is relevant to ISG/labor law.
        
        Args:
            query: User's question
            
        Returns:
            Tuple of (is_relevant, score, reason)
        """
        if not query or len(query.strip()) < 3:
            return False, 0.0, "Query too short"
        
        query_lower = query.lower()
        
        # Step 1: Check for immediate reject keywords
        for keyword in self.IRRELEVANT_KEYWORDS:
            if keyword in query_lower:
                return False, 0.0, f"Irrelevant keyword detected: '{keyword}'"
        
        # Step 2: Calculate ISG relevance score
        score = 0.0
        matched_keywords = []
        
        for keyword in self.ISG_KEYWORDS:
            if keyword in query_lower:
                # Weight by keyword importance
                if len(keyword) > 10 or keyword in ["iş sağlığı", "risk değerlendirmesi"]:
                    weight = 3.0  # high confidence
                elif len(keyword) > 5:
                    weight = 2.0  # medium
                else:
                    weight = 1.0  # low
                
                score += weight
                matched_keywords.append(keyword)
        
        # Step 3: Bonus for regulation-specific terms
        if re.search(r"\d{4}\s*sayılı", query_lower):  # "6331 sayılı"
            score += 3.0
            matched_keywords.append("regulation_number")
        
        if re.search(r"yönetmelik|kanun|tebliğ|genelge", query_lower):
            score += 2.0
            matched_keywords.append("regulation_type")
        
        # Step 4: Verdict
        is_relevant = score >= self.min_score
        
        if is_relevant:
            reason = f"ISG-related (score={score:.1f}, matched={len(matched_keywords)} keywords)"
        else:
            reason = f"Not ISG-related (score={score:.1f} < threshold={self.min_score})"
        
        return is_relevant, score, reason
    
    def filter_with_feedback(self, query: str, verbose: bool = True) -> bool:
        """
        Check relevance and print feedback if verbose.
        
        Args:
            query: User question
            verbose: Print filtering decision
            
        Returns:
            True if relevant, False if should be rejected
        """
        is_relevant, score, reason = self.is_relevant(query)
        
        if verbose:
            if is_relevant:
                print(f"   ✅ Query RELEVANT: {reason}")
            else:
                print(f"   ⚠️  Query FILTERED OUT: {reason}")
        
        return is_relevant


# Quick test
if __name__ == "__main__":
    filter = QueryRelevanceFilter(min_score=1.0)
    
    test_queries = [
        "İşveren iş sağlığı yükümlülükleri neler?",  # should pass
        "Risk değerlendirmesi nasıl yapılır?",       # should pass
        "Uzay istasyonunda çalışırken ne yapmalı?",  # should fail
        "Ay'a seyahat için ISG kuralları var mı?",   # should fail
        "iş güvenliği",                               # should pass (low score)
        "yemek tarifi",                               # should fail
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        filter.filter_with_feedback(query)
