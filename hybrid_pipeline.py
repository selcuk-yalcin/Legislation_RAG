"""
Hybrid RAG Pipeline - Orchestrator
Intelligently routes queries between primary RAG and Gemini fallback
"""

from typing import Dict, Optional
from rag_pipeline import RAGPipeline
from gemini_fallback import GeminiFallback
from confidence_scorer import ConfidenceScorer
from query_normalizer import QueryNormalizer


class HybridRAGOrchestrator:
    """
    Orchestrator that manages the flow between RAG and Gemini fallback
    
    Flow:
    1. Normalize query (expand synonyms)
    2. Try primary RAG search
    3. Score answer confidence
    4. If low confidence → Gemini fallback
    5. Return best answer
    """
    
    # Confidence threshold for fallback decision
    CONFIDENCE_THRESHOLD = 0.60
    
    # Regulation name mapping for fallback
    REGULATION_MAP = {
        "patlayici": "MUHTEMEL PATLAYICI ORTAMDA KULLANILAN TEÇHİZAT",
        "maden": "MADEN İŞYERLERİNDE İŞ SAĞLIĞI VE GÜVENLİĞİ",
        "insaat": "YAPILARDA İŞ SAĞLIĞI VE GÜVENLİĞİ",
        "kimyasal": "KİMYASAL MADDELERLE ÇALIŞMALARDA SAĞLIK VE GÜVENLİK",
        "elektrik": "ELEKTRİK İÇ TESİSLERİ YÖNETMELİĞİ",
        "genel_isg": "İŞ SAĞLIĞI VE GÜVENLİĞİ KANUNU"
    }
    
    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        mongo_collection,
        openrouter_client=None,
        enable_fallback: bool = True
    ):
        """
        Initialize hybrid orchestrator
        
        Args:
            rag_pipeline: Primary RAG pipeline instance
            mongo_collection: MongoDB collection for fallback
            openrouter_client: OpenRouter client (for Gemini 2.0 Flash)
            enable_fallback: Enable Gemini fallback (set False to disable)
        """
        self.rag = rag_pipeline
        self.mongo = mongo_collection
        self.enable_fallback = enable_fallback
        
        # Initialize components
        self.normalizer = QueryNormalizer()
        self.scorer = ConfidenceScorer()
        
        # Initialize Gemini fallback via OpenRouter (if enabled)
        self.gemini = None
        if enable_fallback:
            try:
                self.gemini = GeminiFallback(openrouter_client=openrouter_client)
                print("✅ Hybrid orchestrator initialized with Gemini 2.0 Flash (OpenRouter)")
            except Exception as e:
                print(f"⚠️  Gemini fallback disabled: {e}")
                self.enable_fallback = False
        else:
            print("✅ Hybrid orchestrator initialized (fallback disabled)")
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "rag_success": 0,
            "gemini_fallback": 0,
            "fallback_disabled": 0
        }
    
    def query(self, user_query: str, force_fallback: bool = False) -> Dict:
        """
        Main query method with intelligent routing
        
        Args:
            user_query: User's question
            force_fallback: Force Gemini fallback (for testing)
            
        Returns:
            {
                "answer": str,
                "method": str,  # "primary_rag" or "gemini_fallback"
                "confidence": float,
                "normalized_query": dict,
                "sources": list,  # Only for RAG
                "regulation": str,  # Only for fallback
                "fallback_reason": str  # Why fallback was triggered
            }
        """
        self.stats["total_queries"] += 1
        
        print("\n" + "=" * 80)
        print("🎯 HYBRID RAG ORCHESTRATOR")
        print("=" * 80)
        
        # STEP 1: Query Normalization
        print("\n📝 Step 1: Query Analysis & Normalization...")
        normalized = self.normalizer.normalize_query(user_query)
        
        print(f"   • Original: {user_query}")
        print(f"   • Keywords: {', '.join(normalized['keywords'][:5])}")
        print(f"   • Regulation Type: {normalized['regulation_type']}")
        print(f"   • Expanded Terms: {len(normalized['expanded_terms'])} terms")
        
        # Build expanded query for better vector search
        expanded_query = self.normalizer.build_expanded_query(normalized)
        
        # Force fallback check
        if force_fallback:
            print("\n⚠️  FORCE FALLBACK MODE - Skipping primary RAG")
            return self._execute_fallback(
                user_query,
                normalized,
                "Force fallback requested"
            )
        
        # STEP 2: Primary RAG Search
        print("\n🔍 Step 2: Primary RAG Search...")
        try:
            # Use expanded query for better retrieval
            rag_answer = self.rag.generate_response(expanded_query)
            
            # Get sources for confidence scoring
            sources = self.rag.vectorstore.similarity_search(expanded_query, k=5)
            
            print(f"   ✅ RAG answer generated ({len(rag_answer)} chars)")
            print(f"   📚 Retrieved {len(sources)} sources")
            
        except Exception as e:
            print(f"   ❌ RAG search failed: {e}")
            
            if self.enable_fallback:
                return self._execute_fallback(
                    user_query,
                    normalized,
                    f"RAG search error: {str(e)}"
                )
            else:
                return {
                    "answer": f"Arama sırasında hata oluştu: {str(e)}",
                    "method": "error",
                    "confidence": 0.0,
                    "normalized_query": normalized
                }
        
        # STEP 3: Confidence Scoring
        print("\n⚖️  Step 3: Answer Quality Assessment...")
        
        score_result = self.scorer.score_answer(
            user_query,
            rag_answer,
            sources
        )
        
        confidence = score_result["overall"]
        recommendation = score_result["recommendation"]
        
        print(f"   • Overall Confidence: {confidence:.2f}")
        print(f"   • Component Scores:")
        for component, value in score_result["components"].items():
            print(f"     - {component}: {value:.2f}")
        print(f"   • Recommendation: {recommendation.upper()}")
        
        # STEP 4: Decision - Use RAG or Fallback?
        if confidence >= self.CONFIDENCE_THRESHOLD:
            # HIGH CONFIDENCE - Use RAG answer
            print(f"\n✅ HIGH CONFIDENCE ({confidence:.2f} ≥ {self.CONFIDENCE_THRESHOLD})")
            print("   → Returning PRIMARY RAG answer")
            
            self.stats["rag_success"] += 1
            
            return {
                "answer": rag_answer,
                "method": "primary_rag",
                "confidence": confidence,
                "normalized_query": normalized,
                "sources": sources,
                "confidence_breakdown": score_result["components"]
            }
        
        else:
            # LOW CONFIDENCE - Try Gemini fallback
            print(f"\n⚠️  LOW CONFIDENCE ({confidence:.2f} < {self.CONFIDENCE_THRESHOLD})")
            
            if not self.enable_fallback:
                print("   ⚠️  Fallback disabled - returning RAG answer anyway")
                self.stats["fallback_disabled"] += 1
                
                return {
                    "answer": rag_answer,
                    "method": "primary_rag_low_confidence",
                    "confidence": confidence,
                    "normalized_query": normalized,
                    "sources": sources,
                    "confidence_breakdown": score_result["components"],
                    "warning": "Low confidence but fallback disabled"
                }
            
            # Execute Gemini fallback
            fallback_reason = f"Low confidence ({confidence:.2f})"
            if score_result["components"]["red_flags"] == 0.0:
                fallback_reason += " - 'Not found' phrase detected"
            
            return self._execute_fallback(
                user_query,
                normalized,
                fallback_reason
            )
    
    def _execute_fallback(
        self,
        user_query: str,
        normalized: Dict,
        reason: str
    ) -> Dict:
        """
        Execute Gemini fallback search
        
        Args:
            user_query: Original query
            normalized: Normalized query data
            reason: Why fallback was triggered
        """
        print(f"\n🚨 ACTIVATING GEMINI FALLBACK")
        print(f"   Reason: {reason}")
        
        # Determine which regulation to search
        reg_type = normalized["regulation_type"]
        regulation_name = self.REGULATION_MAP.get(reg_type, self.REGULATION_MAP["genel_isg"])
        
        print(f"   • Target Regulation: {regulation_name}")
        
        try:
            # Execute fallback
            result = self.gemini.fallback_search(
                user_query,
                regulation_name,
                self.mongo
            )
            
            self.stats["gemini_fallback"] += 1
            
            # Add orchestrator metadata
            result["normalized_query"] = normalized
            result["fallback_reason"] = reason
            
            return result
            
        except Exception as e:
            print(f"   ❌ Gemini fallback failed: {e}")
            
            return {
                "answer": f"Hem RAG hem de Gemini fallback başarısız oldu. Hata: {str(e)}",
                "method": "fallback_error",
                "confidence": 0.0,
                "normalized_query": normalized,
                "fallback_reason": reason,
                "error": str(e)
            }
    
    def get_statistics(self) -> Dict:
        """Get orchestrator usage statistics"""
        total = self.stats["total_queries"]
        
        if total == 0:
            return {**self.stats, "percentages": {}}
        
        return {
            **self.stats,
            "percentages": {
                "rag_success": f"{100 * self.stats['rag_success'] / total:.1f}%",
                "gemini_fallback": f"{100 * self.stats['gemini_fallback'] / total:.1f}%",
                "fallback_disabled": f"{100 * self.stats['fallback_disabled'] / total:.1f}%"
            }
        }
    
    def print_statistics(self):
        """Print formatted statistics"""
        stats = self.get_statistics()
        
        print("\n" + "=" * 80)
        print("📊 ORCHESTRATOR STATISTICS")
        print("=" * 80)
        print(f"\nTotal Queries: {stats['total_queries']}")
        
        if stats["total_queries"] > 0:
            print(f"\n✅ Primary RAG Success: {stats['rag_success']} ({stats['percentages']['rag_success']})")
            print(f"🔄 Gemini Fallback: {stats['gemini_fallback']} ({stats['percentages']['gemini_fallback']})")
            
            if stats["fallback_disabled"] > 0:
                print(f"⚠️  Fallback Disabled: {stats['fallback_disabled']} ({stats['percentages']['fallback_disabled']})")


if __name__ == "__main__":
    # Test the orchestrator
    import sys
    import os
    from pymongo import MongoClient
    from mongodb_vector_store import get_mongodb_vectorstore
    from client import create_openrouter_client
    from voyage_reranker import VoyageReranker
    
    print("=" * 80)
    print("🧪 HYBRID RAG ORCHESTRATOR TEST")
    print("=" * 80)
    
    # Initialize components
    print("\n1️⃣  Initializing components...")
    
    try:
        # MongoDB
        MONGO_URI = "mongodb+srv://infera:Hoffnung_1986@mevzuatdb.qqpyi1b.mongodb.net/?appName=mevzuatdb"
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["mevzuat_db"]
        collection = db["documents"]
        
        # RAG components
        vectorstore = get_mongodb_vectorstore()
        openrouter_client = create_openrouter_client()
        reranker = VoyageReranker()
        
        # RAG pipeline
        rag_pipeline = RAGPipeline(openrouter_client, vectorstore, reranker)
        
        print("   ✅ All components initialized")
        
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        sys.exit(1)
    
    # Initialize orchestrator
    print("\n2️⃣  Initializing orchestrator...")
    
    # Check if Gemini is available
    gemini_available = os.getenv('GEMINI_API_KEY') is not None
    
    orchestrator = HybridRAGOrchestrator(
        rag_pipeline=rag_pipeline,
        mongo_collection=collection,
        enable_fallback=gemini_available
    )
    
    # Test queries
    test_queries = [
        {
            "query": "İşverenin iş sağlığı yükümlülükleri nelerdir?",
            "expected": "Should work with RAG (high confidence)"
        },
        {
            "query": "Uzay mekiğinde çalışırken ne yapmalıyım?",
            "expected": "Should trigger fallback (not in regulations)"
        }
    ]
    
    print("\n" + "=" * 80)
    print("3️⃣  Running Test Queries...")
    print("=" * 80)
    
    for idx, test in enumerate(test_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Test {idx}: {test['query']}")
        print(f"Expected: {test['expected']}")
        print("─" * 80)
        
        result = orchestrator.query(test['query'])
        
        print(f"\n📋 RESULT:")
        print(f"   • Method: {result['method']}")
        print(f"   • Confidence: {result.get('confidence', 'N/A')}")
        
        if 'fallback_reason' in result:
            print(f"   • Fallback Reason: {result['fallback_reason']}")
        
        print(f"\n   Answer Preview:")
        answer = result['answer']
        print(f"   {answer[:200]}...")
    
    # Print statistics
    orchestrator.print_statistics()
    
    mongo_client.close()
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
