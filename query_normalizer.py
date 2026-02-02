"""
Query Normalization for Turkish Legal Queries
Handles synonyms, abbreviations, and legal term variations
"""

import re
from typing import Dict, List, Set
from difflib import get_close_matches


class QueryNormalizer:
    """Türkçe legal query normalization with synonym expansion"""
    
    # Legal term synonyms and variations
    LEGAL_SYNONYMS = {
        # Patlayıcı/Yanıcı terms
        "patlayıcı": ["infilak", "parlayıcı", "yanıcı", "tehlikeli madde"],
        "patlama": ["infilak", "patlamalar"],
        
        # İş ilişkileri
        "işveren": ["işletme sahibi", "patron", "müdür", "çalıştıran", "şirket"],
        "işçi": ["çalışan", "personel", "mesai", "memur", "eleman"],
        "çalışan": ["işçi", "personel", "eleman", "görevli"],
        
        # İSG terms
        "isg": ["iş sağlığı", "iş güvenliği", "işçi sağlığı"],
        "güvenlik": ["emniyet", "koruma", "korunma"],
        "sağlık": ["sıhhi", "sağlıklı"],
        "risk": ["tehlike", "tehdit", "zarar"],
        
        # Maden terms
        "maden": ["madencilik", "ocak", "kömür", "taş ocağı"],
        "ocak": ["maden ocağı", "işletme", "kömür ocağı"],
        
        # İnşaat terms
        "inşaat": ["yapı", "bina", "şantiye", "tesis"],
        "şantiye": ["inşaat", "yapı alanı"],
        
        # Yükümlülükler
        "yükümlülük": ["sorumluluk", "görev", "mecburiyet", "vazife"],
        "zorunluluk": ["mecburiyet", "yükümlülük", "gereklilik"],
        
        # Dokümantasyon
        "belge": ["evrak", "döküman", "sertifika", "rapor"],
        "rapor": ["evrak", "belge", "tespit"],
        
        # Eğitim
        "eğitim": ["öğretim", "kurs", "talim"],
        "talim": ["eğitim", "öğretim"],
        
        # Ekipman
        "teçhizat": ["ekipman", "donanım", "alet", "cihaz"],
        "ekipman": ["teçhizat", "alet", "araç"],
        "alet": ["araç", "ekipman", "donanım"],
        
        # Ücret/Maaş
        "ücret": ["maaş", "tazminat", "ödeme", "bedel"],
        "maaş": ["ücret", "aylık", "emolüman"],
        "asgari": ["en az", "minimum", "en düşük"],
    }
    
    # Common abbreviations
    ABBREVIATIONS = {
        "isg": "iş sağlığı ve güvenliği",
        "kkt": "kişisel koruyucu teçhizat",
        "kkd": "kişisel koruyucu donanım",
        "ssk": "sosyal sigortalar kurumu",
        "sgk": "sosyal güvenlik kurumu",
        "işk": "iş kanunu",
    }
    
    # Regulation type keywords
    REGULATION_KEYWORDS = {
        "genel_isg": [
            "iş sağlığı", "iş güvenliği", "çalışan", "işçi", 
            "işveren", "risk", "tehlike"
        ],
        "maden": [
            "maden", "madencilik", "ocak", "kömür", "taş ocağı",
            "kazı", "patlatma", "galeri"
        ],
        "insaat": [
            "inşaat", "yapı", "şantiye", "iskele", "bina",
            "yıkım", "kazı"
        ],
        "patlayici": [
            "patlayıcı", "infilak", "parlayıcı", "yanıcı",
            "tehlikeli madde", "patlama"
        ],
        "kimyasal": [
            "kimyasal", "madde", "toksik", "zehirli",
            "kanserojen", "tehlikeli"
        ],
        "elektrik": [
            "elektrik", "elektrikli", "akım", "gerilim",
            "sigorta", "pano"
        ]
    }
    
    def __init__(self):
        """Initialize normalizer"""
        # Build reverse synonym map for faster lookup
        self.reverse_synonyms = {}
        for key, synonyms in self.LEGAL_SYNONYMS.items():
            for synonym in synonyms:
                if synonym not in self.reverse_synonyms:
                    self.reverse_synonyms[synonym] = []
                self.reverse_synonyms[synonym].append(key)
    
    def expand_abbreviations(self, text: str) -> str:
        """Expand common abbreviations"""
        text_lower = text.lower()
        
        for abbr, full in self.ABBREVIATIONS.items():
            # Replace whole word only (not partial matches)
            pattern = r'\b' + re.escape(abbr) + r'\b'
            text_lower = re.sub(pattern, full, text_lower)
        
        return text_lower
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from query"""
        # Remove common Turkish stopwords
        stopwords = {
            "bir", "bu", "şu", "o", "ve", "veya", "ile", "için",
            "mi", "mı", "mu", "mü", "ne", "nasıl", "nedir", "nelerdir",
            "hangi", "hangisi", "kim", "kime", "nerede", "nereye",
            "niçin", "niye", "neden", "kaç", "kadar"
        }
        
        # Split and clean
        words = re.findall(r'\w+', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def expand_synonyms(self, keywords: List[str]) -> Set[str]:
        """Expand keywords with legal synonyms"""
        expanded = set(keywords)
        
        for keyword in keywords:
            # Direct synonyms
            if keyword in self.LEGAL_SYNONYMS:
                expanded.update(self.LEGAL_SYNONYMS[keyword])
            
            # Reverse lookup
            if keyword in self.reverse_synonyms:
                expanded.update(self.reverse_synonyms[keyword])
        
        return expanded
    
    def detect_regulation_type(self, text: str, keywords: List[str]) -> str:
        """Detect which regulation type the query is about"""
        text_lower = text.lower()
        scores = {}
        
        for reg_type, reg_keywords in self.REGULATION_KEYWORDS.items():
            score = 0
            for keyword in reg_keywords:
                if keyword in text_lower:
                    score += 1
                # Check in extracted keywords too
                for kw in keywords:
                    if keyword in kw or kw in keyword:
                        score += 0.5
            scores[reg_type] = score
        
        # Return highest scoring type, or "genel_isg" as default
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "genel_isg"
    
    def normalize_query(self, query: str) -> Dict:
        """
        Main normalization function
        
        Returns:
            {
                "original": str,
                "normalized": str,
                "keywords": List[str],
                "expanded_terms": Set[str],
                "regulation_type": str,
                "abbreviations_found": List[str]
            }
        """
        # Clean and normalize
        original = query.strip()
        normalized = self.expand_abbreviations(original)
        
        # Extract keywords
        keywords = self.extract_keywords(normalized)
        
        # Expand with synonyms
        expanded_terms = self.expand_synonyms(keywords)
        
        # Detect regulation type
        reg_type = self.detect_regulation_type(normalized, keywords)
        
        # Find abbreviations
        abbrevs_found = [
            abbr for abbr in self.ABBREVIATIONS.keys() 
            if re.search(r'\b' + re.escape(abbr) + r'\b', original.lower())
        ]
        
        return {
            "original": original,
            "normalized": normalized,
            "keywords": keywords,
            "expanded_terms": list(expanded_terms),
            "regulation_type": reg_type,
            "abbreviations_found": abbrevs_found
        }
    
    def build_expanded_query(self, normalized_result: Dict) -> str:
        """
        Build an expanded query string for better vector search
        Combines original + key synonyms
        """
        original = normalized_result['normalized']
        keywords = normalized_result['keywords']
        expanded = normalized_result['expanded_terms']
        
        # Add top 3 most relevant expanded terms
        # (avoid over-expansion which can dilute search)
        top_expansions = []
        for term in expanded:
            if term not in original and len(top_expansions) < 3:
                top_expansions.append(term)
        
        if top_expansions:
            return f"{original} {' '.join(top_expansions)}"
        return original


if __name__ == "__main__":
    # Test the normalizer
    normalizer = QueryNormalizer()
    
    test_queries = [
        "Patlayıcı ortamda işverenin yükümlülükleri nelerdir?",
        "İSG eğitimi nasıl yapılır?",
        "Maden ocağında KKT kullanımı zorunlu mu?",
        "Asgari ücret nasıl belirlenir?",
        "İnşaat şantiyelerinde güvenlik önlemleri nedir?"
    ]
    
    print("=" * 80)
    print("🧪 QUERY NORMALIZER TEST")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\n📝 Original: {query}")
        result = normalizer.normalize_query(query)
        
        print(f"   • Normalized: {result['normalized']}")
        print(f"   • Keywords: {', '.join(result['keywords'])}")
        print(f"   • Regulation: {result['regulation_type']}")
        print(f"   • Expanded ({len(result['expanded_terms'])} terms): {', '.join(list(result['expanded_terms'])[:5])}...")
        
        if result['abbreviations_found']:
            print(f"   • Abbreviations: {', '.join(result['abbreviations_found'])}")
        
        expanded_query = normalizer.build_expanded_query(result)
        print(f"   • Expanded Query: {expanded_query}")
