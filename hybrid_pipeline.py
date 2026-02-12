"""
Hybrid RAG Pipeline - Simplified Orchestrator
Clean 2-tier system: MongoDB RAG → Web Fallback (Serper + Azure DI + MongoDB)
No Gemini fallback, no enhanced fallback, no confidence scorer complexity.

Flow:
0. Query relevance check (filter out irrelevant questions)
1. Normalize query (expand synonyms)
2. Try primary RAG search (MongoDB vector search)
3. Simple quality check (red flags detection)
4. If RAG answer is good → return it
5. If RAG answer is weak → Web Fallback (Serper → fetch links → Azure DI parse → store in MongoDB → answer)
6. If nothing works → guidance message
"""

import re
import random
from typing import Dict, Optional, List
from rag_pipeline import RAGPipeline
from query_normalizer import QueryNormalizer
from query_relevance_filter import QueryRelevanceFilter
from config import MODEL_NAME, TEMPERATURE, MAX_TOKENS


class HybridRAGOrchestrator:
    """
    Simplified 2-tier orchestrator:
      TIER 1: MongoDB RAG (primary search)
      TIER 2: Web Fallback (Serper → Azure DI → MongoDB cache → LLM answer)
    """
    
    # Red flag phrases — if RAG answer contains these, it's likely a bad answer
    # OPTIMIZED: Reduced from 13 to 8 critical flags to avoid false positives
    RED_FLAGS = [
        "bulunamadı",
        "bulunamamıştır", 
        "bilgi bulunmamaktadır",
        "yer almamaktadır",
        "tespit edilememiştir",
        "sağlanan mevzuat",
        "spesifik bir hüküm",
        "mevzuatta bu konuya dair"  # new: catches generic "not in legislation" phrases
    ]
    
    # Guidance messages - varied responses when nothing is found
    NO_RESULT_MESSAGES = [
        "Sağlanan mevzuat kaynaklarında bu konuya ilişkin doğrudan bir hüküm bulunamadı. Sorunuzu daha spesifik bir şekilde (örneğin ilgili sektör, yönetmelik adı veya madde numarası belirterek) yeniden sorabilirsiniz.",
        "Mevcut veritabanında bu soruya karşılık gelen bir düzenleme tespit edilemedi. Farklı anahtar kelimeler kullanarak veya sorunuzu daraltarak tekrar deneyebilirsiniz.",
        "Bu konuda doğrudan bir mevzuat hükmüne ulaşılamadı. Sorunuzu belirli bir kanun veya yönetmelik adı ile daraltmanız daha isabetli sonuçlar verebilir.",
        "Aradığınız bilgiye mevcut kaynaklarda rastlanmadı. Sorunuzu sektöre özel detaylar ekleyerek (örneğin inşaat, maden, kimya sektörü gibi) tekrar sormanızı öneriyoruz.",
        "Bu konuya ilişkin bir düzenlemeye kaynaklarda ulaşılamadı. Sorunuzu farklı bir açıdan veya daha detaylı ifade ederek yeniden deneyebilirsiniz.",
    ]
    
    @classmethod
    def _get_guidance_message(cls):
        """Return a varied guidance message each time"""
        return random.choice(cls.NO_RESULT_MESSAGES)
    
    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        mongo_collection,
        openrouter_client=None,
        enable_fallback: bool = True  # kept for backward compat, ignored
    ):
        self.rag = rag_pipeline
        self.mongo = mongo_collection
        self.openrouter_client = openrouter_client
        
        # Query normalizer (synonym expansion, abbreviation handling)
        self.normalizer = QueryNormalizer()
        
        # Query relevance filter (filter out irrelevant questions)
        self.relevance_filter = QueryRelevanceFilter(min_score=1.0)  # permissive threshold
        
        # Web Fallback Pipeline (Serper + Azure DI + MongoDB)
        self.web_pipeline = None
        try:
            from web_fallback_pipeline import WebFallbackPipeline
            self.web_pipeline = WebFallbackPipeline(openrouter_client=openrouter_client)
            if not self.web_pipeline.enabled:
                self.web_pipeline = None
                print("⚠️  Web fallback disabled (missing SERPER_API_KEY)")
        except Exception as e:
            print(f"⚠️  Web fallback pipeline disabled: {e}")
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "rag_success": 0,
            "web_fallback": 0,
            "guidance": 0,
        }
        
        print("✅ Hybrid orchestrator initialized (2-tier: RAG → Web Fallback)")
    
    # ──────────────────────────────────────────────
    # Simple quality check (replaces confidence_scorer)
    # ──────────────────────────────────────────────
    
    def _has_red_flags(self, answer: str) -> bool:
        """Check if RAG answer contains 'not found' type phrases"""
        answer_lower = answer.lower()
        for flag in self.RED_FLAGS:
            if flag in answer_lower:
                return True
        return False
    
    def _is_answer_good(self, answer: str) -> bool:
        """
        Simple quality gate (OPTIMIZED):
        - Answer must be at least 50 chars (reduced from 80 to avoid false negatives)
        - Answer must NOT contain critical red flag phrases
        
        Why 50 chars? Short but precise answers like:
        "İşveren 3 iş günü içinde SGK'ya bildirimde bulunmalıdır."
        are only ~60 chars but perfectly valid.
        """
        if not answer or len(answer.strip()) < 50:
            return False
        if self._has_red_flags(answer):
            return False
        return True
    
    # ──────────────────────────────────────────────
    # Main query method
    # ──────────────────────────────────────────────
    
    def query(self, user_query: str, force_fallback: bool = False) -> Dict:
        """
        Main query method — clean 2-tier routing.
        
        Args:
            user_query: User's question
            force_fallback: Force web fallback (for testing)
            
        Returns:
            Dict with answer, method, confidence, sources etc.
        """
        self.stats["total_queries"] += 1
        
        print("\n" + "=" * 80)
        print("🎯 HYBRID RAG ORCHESTRATOR (2-Tier)")
        print("=" * 80)
        
        # ── STEP 0: Relevance Check ──
        print("\n🔍 Step 0: Query Relevance Check...")
        is_relevant, score, reason = self.relevance_filter.is_relevant(user_query)
        print(f"   • Relevance Score: {score:.1f}")
        print(f"   • {reason}")
        
        if not is_relevant:
            print("\n⚠️  Query filtered as IRRELEVANT to ISG/labor law")
            self.stats["guidance"] += 1
            return {
                "answer": self._get_guidance_message(),
                "method": "guidance",
                "confidence": 0.0,
                "sources": [],
                "fallback_reason": f"Query not related to ISG (score={score:.1f})",
            }
        
        # ── STEP 1: Query Normalization ──
        print("\n📝 Step 1: Query Normalization...")
        normalized = self.normalizer.normalize_query(user_query)
        expanded_query = self.normalizer.build_expanded_query(normalized)
        
        print(f"   • Original: {user_query}")
        print(f"   • Keywords: {', '.join(normalized['keywords'][:5])}")
        print(f"   • Regulation Type: {normalized['regulation_type']}")
        
        # Force web fallback (for testing)
        if force_fallback:
            print("\n⚠️  FORCE WEB FALLBACK MODE")
            return self._execute_web_fallback(user_query, normalized)
        
        # ── STEP 2: Primary RAG Search ──
        print("\n🔍 Step 2: Primary RAG Search (MongoDB)...")
        try:
            rag_result = self.rag.generate_response(expanded_query)
            
            # Handle both string and dict return formats
            if isinstance(rag_result, dict):
                rag_answer = rag_result.get('answer', '')
                rag_sources = rag_result.get('sources', [])
            else:
                rag_answer = rag_result
                rag_sources = []
            
            # Get sources if not returned by RAG
            if not rag_sources:
                rag_sources = self.rag.vectorstore.similarity_search(expanded_query, k=5)
            
            print(f"   ✅ RAG answer: {len(rag_answer)} chars, {len(rag_sources)} sources")
            
        except Exception as e:
            print(f"   ❌ RAG search failed: {e}")
            # RAG failed entirely → go to web fallback
            return self._execute_web_fallback(user_query, normalized, 
                                               reason=f"RAG error: {str(e)}")
        
        # ── STEP 3: Quality Check ──
        print("\n⚖️  Step 3: Quality Check...")
        answer_is_good = self._is_answer_good(rag_answer)
        
        if answer_is_good:
            # ✅ RAG answer is good — return it
            print(f"   ✅ Answer PASSED quality check")
            self.stats["rag_success"] += 1
            
            return {
                "answer": rag_answer,
                "method": "primary_rag",
                "confidence": 0.85,
                "normalized_query": normalized,
                "sources": rag_sources,
            }
        else:
            # ❌ RAG answer is weak — try web fallback
            reason = "Red flags detected" if self._has_red_flags(rag_answer) else "Answer too short"
            print(f"   ⚠️  Answer FAILED quality check ({reason})")
            print("   → Activating Web Fallback...")
            
            return self._execute_web_fallback(user_query, normalized, reason=reason)
    
    # ──────────────────────────────────────────────
    # Web Fallback (TIER 2)
    # ──────────────────────────────────────────────
    
    def _execute_web_fallback(
        self, 
        user_query: str, 
        normalized: Dict, 
        reason: str = ""
    ) -> Dict:
        """
        Execute web fallback pipeline:
        Serper search → fetch full content from links → Azure DI parse → 
        chunk → store in MongoDB web_search collection → generate answer
        """
        if not self.web_pipeline:
            print("   ⚠️  Web fallback not available, returning guidance")
            self.stats["guidance"] += 1
            return {
                "answer": self._get_guidance_message(),
                "method": "guidance",
                "confidence": 0.1,
                "normalized_query": normalized,
                "sources": [],
                "fallback_reason": reason or "Web fallback not configured",
            }
        
        print(f"\n🌐 Web Fallback Pipeline...")
        if reason:
            print(f"   Reason: {reason}")
        
        try:
            # Use regulation type as hint for better search
            reg_hint = normalized.get("regulation_type", "")
            
            web_result = self.web_pipeline.execute(
                user_query, 
                regulation_hint=reg_hint if reg_hint else None
            )
            
            if web_result and web_result.get("answer"):
                self.stats["web_fallback"] += 1
                web_result["normalized_query"] = normalized
                web_result["fallback_reason"] = reason
                print("   ✅ Web Fallback succeeded!")
                return web_result
            else:
                print("   ⚠️  Web Fallback returned no results")
        except Exception as e:
            print(f"   ❌ Web Fallback error: {e}")
        
        # Nothing worked → guidance
        self.stats["guidance"] += 1
        return {
            "answer": self._get_guidance_message(),
            "method": "guidance",
            "confidence": 0.1,
            "normalized_query": normalized,
            "sources": [],
            "fallback_reason": reason or "All methods exhausted",
        }
    
    # ──────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────
    
    def get_statistics(self) -> Dict:
        """Get orchestrator usage statistics"""
        total = self.stats["total_queries"]
        
        if total == 0:
            return {**self.stats, "percentages": {}}
        
        return {
            **self.stats,
            "percentages": {
                "rag_success": f"{100 * self.stats['rag_success'] / total:.1f}%",
                "web_fallback": f"{100 * self.stats['web_fallback'] / total:.1f}%",
                "guidance": f"{100 * self.stats['guidance'] / total:.1f}%",
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
            print(f"\n✅ RAG Success: {stats['rag_success']} ({stats['percentages']['rag_success']})")
            print(f"🌐 Web Fallback: {stats['web_fallback']} ({stats['percentages']['web_fallback']})")
            print(f"📋 Guidance: {stats['guidance']} ({stats['percentages']['guidance']})")
