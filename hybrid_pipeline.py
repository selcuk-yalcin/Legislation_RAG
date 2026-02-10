"""
Hybrid RAG Pipeline - Orchestrator
Intelligently routes queries between primary RAG and Gemini fallback
Enhanced: 3-tier confidence system - never returns empty answers
"""

import re
from typing import Dict, Optional, List
from rag_pipeline import RAGPipeline
from gemini_fallback import GeminiFallback
from confidence_scorer import ConfidenceScorer
from query_normalizer import QueryNormalizer
from config import MODEL_NAME, TEMPERATURE, MAX_TOKENS


class HybridRAGOrchestrator:
    """
    Orchestrator that manages the flow between RAG and Gemini fallback
    
    Enhanced Flow:
    1. Normalize query (expand synonyms)
    2. Try primary RAG search
    3. Score answer confidence
    4. 3-tier decision:
       - HIGH (≥0.60): Return RAG answer as-is
       - MEDIUM (0.35-0.60): Enrich RAG answer with warning prefix
       - LOW (<0.35): 3-strategy enhanced search, never return empty
    5. Return best answer — ALWAYS with content
    """
    
    # Confidence thresholds for 3-tier system
    HIGH_CONFIDENCE_THRESHOLD = 0.60
    MEDIUM_CONFIDENCE_THRESHOLD = 0.35
    
    # Regulation name mapping for fallback
    REGULATION_MAP = {
        "patlayici": "MUHTEMEL PATLAYICI ORTAMDA KULLANILAN TEÇHİZAT",
        "maden": "İŞ KANUNU",
        "insaat": "YAPILARDA İŞ SAĞLIĞI VE GÜVENLİĞİ",
        "kimyasal": "KİMYASAL MADDELERLE ÇALIŞMALARDA SAĞLIK VE GÜVENLİK",
        "elektrik": "ELEKTRİK İÇ TESİSLERİ YÖNETMELİĞİ",
        "genel_isg": "İŞ SAĞLIĞI VE GÜVENLİĞİ KANUNU"
    }
    
    # Warning prefix for medium-confidence answers
    MEDIUM_CONFIDENCE_PREFIX = "⚠️ **Mevzuatta bu konuya doğrudan karşılık gelen bir hüküm bulunamadı, ancak ilgili düzenlemeler çerçevesinde şu bilgiler verilebilir:**\n\n"
    
    # No-result guidance template
    NO_RESULT_GUIDANCE = """⚠️ **Mevzuatta bu konuya doğrudan karşılık gelen bir hüküm bulunamadı.**

Sorunuzla ilgili inceleyebileceğiniz mevzuat kaynakları:

• **6331 Sayılı İş Sağlığı ve Güvenliği Kanunu** — İSG'nin temel çerçeve kanunu
• **İş Sağlığı ve Güvenliği Risk Değerlendirmesi Yönetmeliği** — Risk analizi prosedürleri
• **İşyerlerinde Acil Durumlar Hakkında Yönetmelik** — Acil durum planları
• **Çalışanların İş Sağlığı ve Güvenliği Eğitimlerinin Usul ve Esasları Hakkında Yönetmelik** — Eğitim gereksinimleri

💡 Daha spesifik bir soru sorarsanız (ör. sektör, konu veya yönetmelik adı belirterek) daha doğru sonuçlar alabiliriz.
"""
    
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
        self.openrouter_client = openrouter_client
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
            "rag_enriched": 0,
            "enhanced_fallback": 0,
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
        
        # STEP 4: Decision - 3-Tier Confidence System
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            # TIER 1: HIGH CONFIDENCE - Use RAG answer as-is
            print(f"\n✅ HIGH CONFIDENCE ({confidence:.2f} ≥ {self.HIGH_CONFIDENCE_THRESHOLD})")
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
        
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            # TIER 2: MEDIUM CONFIDENCE - Enrich RAG answer with warning prefix
            print(f"\n⚠️  MEDIUM CONFIDENCE ({confidence:.2f}) — Enriching answer with warning")
            print("   → Returning ENRICHED RAG answer")
            
            self.stats["rag_enriched"] += 1
            
            # Strip existing source section if present, will re-add after prefix
            answer_text = rag_answer
            source_separator = "═" * 70
            if source_separator in answer_text:
                answer_text = answer_text[:answer_text.index(source_separator)].strip()
                source_section = rag_answer[rag_answer.index(source_separator) - 2:]
            else:
                source_section = ""
            
            enriched_answer = self.MEDIUM_CONFIDENCE_PREFIX + answer_text
            if source_section:
                enriched_answer += "\n\n" + source_section
            
            return {
                "answer": enriched_answer,
                "method": "primary_rag_enriched",
                "confidence": confidence,
                "normalized_query": normalized,
                "sources": sources,
                "confidence_breakdown": score_result["components"],
                "enrichment": "medium_confidence_warning"
            }
        
        else:
            # TIER 3: LOW CONFIDENCE - Enhanced multi-strategy search
            print(f"\n🚨 LOW CONFIDENCE ({confidence:.2f} < {self.MEDIUM_CONFIDENCE_THRESHOLD})")
            print("   → Activating ENHANCED FALLBACK (3-strategy search)")
            
            # Try enhanced fallback first
            enhanced_result = self._execute_enhanced_fallback(
                user_query, expanded_query, normalized
            )
            
            if enhanced_result and enhanced_result.get("confidence", 0) > 0.3:
                self.stats["enhanced_fallback"] += 1
                return enhanced_result
            
            # If enhanced fallback also failed, try Gemini
            if self.enable_fallback:
                fallback_reason = f"Low confidence ({confidence:.2f})"
                if score_result["components"]["red_flags"] == 0.0:
                    fallback_reason += " - 'Not found' phrase detected"
                
                gemini_result = self._execute_fallback(
                    user_query,
                    normalized,
                    fallback_reason
                )
                
                # If Gemini also failed or errored, return enhanced fallback or guidance
                if gemini_result.get("confidence", 0) > 0:
                    return gemini_result
            
            # ABSOLUTE LAST RESORT: Return enhanced fallback result or guidance
            if enhanced_result and enhanced_result.get("answer"):
                return enhanced_result
            
            # Return guidance — NEVER empty
            return {
                "answer": self.NO_RESULT_GUIDANCE,
                "method": "guidance",
                "confidence": 0.1,
                "normalized_query": normalized,
                "sources": [],
                "note": "No relevant content found — providing regulation guidance"
            }
    
    def _simplify_query(self, query: str) -> str:
        """Simplify query by removing question words and keeping core concepts"""
        # Remove Turkish question words
        question_words = [
            "nasıl", "nedir", "nelerdir", "ne", "hangi", "hangisi",
            "kim", "kime", "nerede", "nereye", "kaç", "kadar",
            "mi", "mı", "mu", "mü", "midir", "mıdır", "mudur", "müdür"
        ]
        words = query.split()
        simplified = [w for w in words if w.lower().strip("?.,!") not in question_words]
        return " ".join(simplified).strip("?.,! ")
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract core keywords for broad keyword search"""
        stopwords = {
            "bir", "bu", "şu", "o", "ve", "veya", "ile", "için", "de", "da",
            "mi", "mı", "mu", "mü", "ne", "nasıl", "nedir", "nelerdir",
            "hangi", "hangisi", "kim", "kime", "nerede", "nereye",
            "niçin", "niye", "neden", "kaç", "kadar", "olan", "olarak",
            "gibi", "daha", "çok", "en", "var", "yok", "hem"
        }
        words = re.findall(r'\w+', query.lower())
        return [w for w in words if w not in stopwords and len(w) > 2]
    
    def _deduplicate_docs(self, docs: List) -> List:
        """Remove duplicate documents based on content hash"""
        seen = set()
        unique = []
        for doc in docs:
            content_key = doc.page_content[:200] if hasattr(doc, 'page_content') else str(doc)[:200]
            if content_key not in seen:
                seen.add(content_key)
                unique.append(doc)
        return unique
    
    def _build_enriched_context(self, docs: List) -> str:
        """Build context string from documents with source info"""
        if not docs:
            return ""
        
        context_parts = []
        for idx, doc in enumerate(docs, 1):
            title = doc.metadata.get('document_title', doc.metadata.get('source_file', 'Bilinmeyen'))
            # Clean title
            title = title.replace('.pdf', '').replace('.PDF', '').replace('_', ' ').strip()
            context_parts.append(f"KAYNAK [{title}]: {doc.page_content}")
        
        return "\n\n".join(context_parts)
    
    def _execute_enhanced_fallback(
        self,
        original_query: str,
        expanded_query: str,
        normalized: Dict
    ) -> Optional[Dict]:
        """
        Enhanced 3-strategy fallback search — tries multiple approaches
        to find relevant content before giving up.
        
        Strategies:
        1. Original query (already failed, but get the docs)
        2. Simplified query (remove question words, keep concepts)
        3. Keyword-based broad search
        
        Then: deduplicate, rerank, generate enriched answer with warning prefix
        """
        print(f"\n🔄 ENHANCED FALLBACK: 3-Strategy Search")
        
        all_docs = []
        
        # Strategy 1: Use expanded query (slightly different from original)
        try:
            print("   📌 Strategy 1: Expanded query search...")
            docs1 = self.rag.vectorstore.similarity_search(expanded_query, k=20)
            all_docs.extend(docs1)
            print(f"      Found {len(docs1)} documents")
        except Exception as e:
            print(f"      ❌ Strategy 1 failed: {e}")
        
        # Strategy 2: Simplified query
        try:
            simplified = self._simplify_query(original_query)
            print(f"   📌 Strategy 2: Simplified query: '{simplified}'")
            if simplified and simplified != original_query:
                docs2 = self.rag.vectorstore.similarity_search(simplified, k=20)
                all_docs.extend(docs2)
                print(f"      Found {len(docs2)} documents")
        except Exception as e:
            print(f"      ❌ Strategy 2 failed: {e}")
        
        # Strategy 3: Keyword-based search
        try:
            keywords = self._extract_keywords(original_query)
            keyword_query = " ".join(keywords[:5])
            print(f"   📌 Strategy 3: Keyword search: '{keyword_query}'")
            if keyword_query:
                docs3 = self.rag.vectorstore.similarity_search(keyword_query, k=20)
                all_docs.extend(docs3)
                print(f"      Found {len(docs3)} documents")
        except Exception as e:
            print(f"      ❌ Strategy 3 failed: {e}")
        
        if not all_docs:
            print("   ❌ All 3 strategies returned 0 documents")
            return None
        
        # Deduplicate
        unique_docs = self._deduplicate_docs(all_docs)
        print(f"\n   📊 Total unique documents: {len(unique_docs)}")
        
        # Rerank with Voyage if available
        if self.rag.reranker and len(unique_docs) > 0:
            try:
                print("   🎯 Reranking with Voyage...")
                reranked = self.rag.reranker.rerank_documents(
                    original_query, unique_docs, top_k=min(8, len(unique_docs))
                )
                unique_docs = reranked
                print(f"   ✅ Reranked to top {len(reranked)} documents")
            except Exception as e:
                print(f"   ⚠️  Reranking failed, using top docs: {e}")
                unique_docs = unique_docs[:8]
        else:
            unique_docs = unique_docs[:8]
        
        # Build enriched context
        context = self._build_enriched_context(unique_docs)
        
        if not context.strip():
            return None
        
        # Generate enriched answer with LLM
        try:
            enriched_answer = self._generate_enriched_answer(
                original_query, context, unique_docs
            )
            
            if enriched_answer:
                return {
                    "answer": enriched_answer,
                    "method": "enhanced_fallback",
                    "confidence": 0.45,
                    "normalized_query": normalized,
                    "sources": unique_docs,
                    "strategies_used": 3,
                    "total_docs_found": len(all_docs),
                    "unique_docs_used": len(unique_docs)
                }
        except Exception as e:
            print(f"   ❌ Enhanced answer generation failed: {e}")
        
        return None
    
    def _generate_enriched_answer(
        self,
        query: str,
        context: str,
        docs: List
    ) -> Optional[str]:
        """
        Generate an answer from the closest relevant documents
        with appropriate warning prefix
        """
        print("   💡 Generating enriched answer with warning prefix...")
        
        enriched_prompt = f"""
Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış bir danışmansın.

DURUM: Kullanıcının sorusu için birebir eşleşen bir hüküm bulunamadı, ancak aşağıda 
EN YAKIN ilgili mevzuat metinleri sunulmaktadır. Bu metinleri kullanarak soruyu 
elinden geldiğince yanıtla.

ÖNEMLİ KURALLAR:
1. Yanıtın MUTLAKA şu uyarıyla başlamalıdır:
   "⚠️ **Mevzuatta bu konuya doğrudan karşılık gelen bir hüküm bulunamadı, ancak ilgili düzenlemeler çerçevesinde şu bilgiler verilebilir:**"
2. Ardından mevcut metinlerden çıkarılabilecek EN YAKIN bilgileri sun
3. Kaynak referanslarını köşeli parantez içinde SADECE yönetmelik/kanun adı olarak yaz
4. "Fıkra", "Bent", "Madde" kelimelerini ASLA kullanma
5. Dosya adı (.pdf) kullanma
6. Spekülatif bilgi verme — sadece metinlerdeki bilgileri kullan
7. Eğer metinlerde hiç ilgili bilgi yoksa bile, hangi mevzuatın incelenmesi gerektiğini öner

Mevzuat İçeriği:
----------------------------------
{context}
----------------------------------

Kullanıcı Sorusu: {query}

Yanıt (Uyarı prefixli, Kaynaklı):"""
        
        messages = [
            {
                "role": "system",
                "content": """Sen İSG mevzuatı danışmanısın. Kullanıcının sorusuna birebir cevap bulunamadığında
bile en yakın ilgili bilgileri sun. ASLA boş cevap verme. Her zaman yardımcı ol."""
            },
            {"role": "user", "content": enriched_prompt}
        ]
        
        try:
            response = self.rag.client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            
            answer_text = response.choices[0].message.content
            
            # Add sources section
            sources_html = self._format_enhanced_sources(docs)
            
            return answer_text + sources_html
            
        except Exception as e:
            print(f"   ❌ LLM generation failed: {e}")
            return None
    
    def _format_enhanced_sources(self, docs: List) -> str:
        """Format source documents for enhanced fallback"""
        if not docs:
            return ""
        
        sources = "\n\n" + "═" * 70 + "\n"
        sources += "📚 CEVABINIZ İÇİN KULLANILAN KAYNAKLAR\n"
        sources += "═" * 70 + "\n\n"
        
        for idx, doc in enumerate(docs, 1):
            title = doc.metadata.get('document_title', doc.metadata.get('source_file', 'Bilinmeyen Belge'))
            title = title.replace('.pdf', '').replace('.PDF', '').replace('_', ' ').strip()
            
            sources += f"📄 Kaynak {idx}: {title}\n"
            sources += "─" * 70 + "\n"
            
            content_preview = doc.page_content.replace('\n', ' ').strip()
            sources += f"💬 Alıntı: \"{content_preview}\"\n\n"
        
        sources += "═" * 70 + "\n"
        sources += "💡 Not: En yakın ilgili mevzuat metinleri kullanılarak yanıt üretilmiştir.\n"
        return sources
    
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
                "rag_enriched": f"{100 * self.stats['rag_enriched'] / total:.1f}%",
                "enhanced_fallback": f"{100 * self.stats['enhanced_fallback'] / total:.1f}%",
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
            print(f"\n✅ Primary RAG Success (High): {stats['rag_success']} ({stats['percentages']['rag_success']})")
            print(f"⚠️  Enriched RAG (Medium): {stats['rag_enriched']} ({stats['percentages']['rag_enriched']})")
            print(f"🔄 Enhanced Fallback (Low): {stats['enhanced_fallback']} ({stats['percentages']['enhanced_fallback']})")
            print(f"🚀 Gemini Fallback: {stats['gemini_fallback']} ({stats['percentages']['gemini_fallback']})")
            
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
