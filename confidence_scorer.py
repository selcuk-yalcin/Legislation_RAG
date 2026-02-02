"""
Confidence Scorer for RAG Answers
Determines if answer quality is sufficient or if fallback is needed
"""

from typing import List, Dict
import re


class ConfidenceScorer:
    """Answer quality assessment for hybrid RAG system"""
    
    # Red flag phrases indicating low confidence
    RED_FLAGS = [
        "bulunamadı",
        "bulunamaz",
        "bulunmamaktadır",
        "bulunamamıştır",  # Past tense passive
        "bulunmamıştır",   # Past tense passive variant
        "bilgi yok",
        "mevcut değil",
        "belirtilmemiş",
        "açık değil",
        "bilgi bulunmamaktadır",
        "yer almamaktadır",
        "değildir",  # Too vague
        "bilinmemektedir",
        "tespit edilememiştir",
        "sağlanan mevzuat",  # RAG couldn't find info
        "spesifik bir hüküm"  # No specific provision found
    ]
        "belirtilmemiş",
        "açık değil",
        "bilgi bulunmamaktadır",
        "yer almamaktadır",
        "değildir",  # Too vague
        "bilinmemektedir",
        "tespit edilememiştir"
    ]
    
    # Positive signals
    POSITIVE_SIGNALS = [
        "madde",  # MADDE citation
        "fıkra",  # Detailed citation
        "bent",   # Very detailed
        "göre",   # References law
        "uyarınca",  # Legal language
        "hüküm",  # Legal provision
        "kanun",  # Law reference
        "yönetmelik"  # Regulation reference
    ]
    
    def __init__(self, min_answer_length: int = 50):
        """
        Args:
            min_answer_length: Minimum acceptable answer length
        """
        self.min_answer_length = min_answer_length
    
    def check_red_flags(self, answer: str) -> bool:
        """Check if answer contains 'not found' type phrases"""
        answer_lower = answer.lower()
        
        for flag in self.RED_FLAGS:
            if flag in answer_lower:
                return True
        
        return False
    
    def count_positive_signals(self, answer: str) -> int:
        """Count positive legal language indicators"""
        answer_lower = answer.lower()
        count = 0
        
        for signal in self.POSITIVE_SIGNALS:
            # Count occurrences (capped at 3 per signal)
            occurrences = min(3, answer_lower.count(signal))
            count += occurrences
        
        return count
    
    def calculate_source_relevance(self, sources: List) -> float:
        """
        Calculate average relevance of source documents
        
        Args:
            sources: List of Document objects with metadata
        """
        if not sources:
            return 0.0
        
        total_score = 0.0
        scored_sources = 0
        
        for source in sources:
            metadata = source.metadata if hasattr(source, 'metadata') else source.get('metadata', {})
            
            # Check for relevance score from reranker
            if 'relevance_score' in metadata:
                total_score += metadata['relevance_score']
                scored_sources += 1
            # Fallback: estimate from metadata completeness
            else:
                estimate = 0.5  # baseline
                
                # Has MADDE number
                if metadata.get('madde_number') and metadata.get('madde_number') != 'Unknown':
                    estimate += 0.2
                
                # Is complete MADDE
                if metadata.get('is_complete_madde'):
                    estimate += 0.2
                
                # Has parent content
                if metadata.get('parent_article_content'):
                    estimate += 0.1
                
                total_score += estimate
                scored_sources += 1
        
        return total_score / scored_sources if scored_sources > 0 else 0.5
    
    def score_answer(
        self, 
        query: str, 
        answer: str, 
        sources: List
    ) -> Dict[str, float]:
        """
        Comprehensive answer quality scoring
        
        Args:
            query: Original user query
            answer: Generated answer
            sources: Retrieved source documents
            
        Returns:
            {
                "overall": float (0.0 - 1.0),
                "components": {
                    "length": float,
                    "red_flags": float,
                    "positive_signals": float,
                    "source_relevance": float,
                    "citation_quality": float
                },
                "recommendation": str ("use" or "fallback")
            }
        """
        
        scores = {}
        
        # Component 1: Answer length
        answer_length = len(answer.strip())
        if answer_length < self.min_answer_length:
            scores['length'] = 0.0
        elif answer_length < 100:
            scores['length'] = 0.5
        elif answer_length < 200:
            scores['length'] = 0.7
        else:
            scores['length'] = 1.0
        
        # Component 2: Red flags (instant disqualifier)
        has_red_flags = self.check_red_flags(answer)
        scores['red_flags'] = 0.0 if has_red_flags else 1.0
        
        # INSTANT REJECTION: If red flags detected, return 0.0 immediately
        if has_red_flags:
            return {
                "overall": 0.0,
                "components": {
                    'length': 0.0,
                    'red_flags': 0.0,
                    'positive_signals': 0.0,
                    'source_relevance': 0.0,
                    'citation_quality': 0.0
                },
                "recommendation": "fallback",
                "reason": "Red flag detected - insufficient information in sources"
            }
        
        # Component 3: Positive signals
        positive_count = self.count_positive_signals(answer)
        scores['positive_signals'] = min(1.0, positive_count / 5.0)
        
        # Component 4: Source relevance
        scores['source_relevance'] = self.calculate_source_relevance(sources)
        
        # Component 5: Citation quality
        citation_score = 0.0
        
        # Has MADDE citations
        madde_pattern = r'MADDE\s*\d+'
        madde_matches = re.findall(madde_pattern, answer, re.IGNORECASE)
        if madde_matches:
            citation_score += 0.5
        
        # Has document references
        if len(sources) > 0:
            source_titles = [
                s.metadata.get('document_title', '') if hasattr(s, 'metadata') 
                else s.get('metadata', {}).get('document_title', '')
                for s in sources
            ]
            
            # Check if answer mentions source documents
            for title in source_titles:
                if title and len(title) > 10:
                    # Check for partial title match (at least 3 words)
                    title_words = title.split()[:5]
                    for word in title_words:
                        if len(word) > 4 and word.lower() in answer.lower():
                            citation_score += 0.1
                            break
        
        scores['citation_quality'] = min(1.0, citation_score)
        
        # Overall score (weighted average)
        weights = {
            'length': 0.10,
            'red_flags': 0.40,  # Most important
            'positive_signals': 0.20,
            'source_relevance': 0.20,
            'citation_quality': 0.10
        }
        
        overall = sum(scores[k] * weights[k] for k in weights.keys())
        
        # Recommendation
        recommendation = "use" if overall >= 0.6 else "fallback"
        
        return {
            "overall": overall,
            "components": scores,
            "recommendation": recommendation
        }


if __name__ == "__main__":
    # Test the scorer
    scorer = ConfidenceScorer()
    
    # Mock sources
    class MockSource:
        def __init__(self, metadata):
            self.metadata = metadata
    
    test_cases = [
        {
            "name": "Good Answer",
            "query": "İşverenin yükümlülükleri nelerdir?",
            "answer": "İş Sağlığı ve Güvenliği Kanunu MADDE 4'e göre işverenin yükümlülükleri şunlardır: 1) Risk değerlendirmesi yapmak, 2) İSG hizmetlerini sağlamak, 3) Çalışanları eğitmek. Bu hükümler 6331 sayılı Kanunun 4. maddesinde açıkça belirtilmiştir.",
            "sources": [
                MockSource({"madde_number": "4", "is_complete_madde": True, "document_title": "İŞ SAĞLIĞI VE GÜVENLİĞİ KANUNU"})
            ]
        },
        {
            "name": "Bad Answer (Not Found)",
            "query": "Ay sonu tatili kaç gündür?",
            "answer": "Bu konuda mevzuatta açık bir bilgi bulunmamaktadır.",
            "sources": []
        },
        {
            "name": "Medium Answer (Vague)",
            "query": "Asgari ücret ne kadardır?",
            "answer": "Asgari ücret yılda bir kez belirlenir.",
            "sources": [
                MockSource({"madde_number": "Unknown", "is_complete_madde": False})
            ]
        }
    ]
    
    print("=" * 80)
    print("🧪 CONFIDENCE SCORER TEST")
    print("=" * 80)
    
    for test in test_cases:
        print(f"\n📝 Test: {test['name']}")
        print(f"   Query: {test['query']}")
        print(f"   Answer: {test['answer'][:80]}...")
        
        result = scorer.score_answer(
            test['query'],
            test['answer'],
            test['sources']
        )
        
        print(f"\n   📊 Scores:")
        print(f"      • Overall: {result['overall']:.2f}")
        print(f"      • Length: {result['components']['length']:.2f}")
        print(f"      • Red Flags: {result['components']['red_flags']:.2f}")
        print(f"      • Positive Signals: {result['components']['positive_signals']:.2f}")
        print(f"      • Source Relevance: {result['components']['source_relevance']:.2f}")
        print(f"      • Citation Quality: {result['components']['citation_quality']:.2f}")
        print(f"\n   🎯 Recommendation: {result['recommendation'].upper()}")
