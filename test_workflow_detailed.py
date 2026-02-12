"""
Detailed Workflow Test - 2-Tier System
Tests: RAG → Web Fallback → Guidance

Adım adım test eder:
1. MongoDB'de var olan sorular (RAG success beklenir)
2. MongoDB'de olmayan ama web'de bulunabilecek sorular (Web fallback beklenir)
3. Hiçbir yerde olmayan sorular (Guidance beklenir)
"""

import os
import sys
import time
from datetime import datetime
from pymongo import MongoClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from client import create_openrouter_client
from mongodb_vector_store import get_mongodb_vectorstore
from voyage_reranker import VoyageReranker
from rag_pipeline import RAGPipeline
from hybrid_pipeline import HybridRAGOrchestrator


class WorkflowTester:
    """Detailed workflow tester with step-by-step logging"""
    
    def __init__(self):
        self.results = []
        self.test_start = datetime.now()
        
        print("=" * 100)
        print("🧪 WORKFLOW TEST — 2-Tier System (RAG → Web Fallback)")
        print("=" * 100)
        
        # Initialize components
        print("\n📦 Step 1: Initializing components...")
        try:
            self.openrouter_client = create_openrouter_client()
            print("   ✅ OpenRouter client ready")
            
            self.vectorstore = get_mongodb_vectorstore()
            stats = self.vectorstore.get_collection_stats()
            print(f"   ✅ MongoDB connected: {stats['total_documents']} documents")
            
            self.reranker = VoyageReranker()
            print("   ✅ Voyage reranker ready")
            
            self.rag = RAGPipeline(self.openrouter_client, self.vectorstore, self.reranker)
            print("   ✅ RAG pipeline ready")
            
            # Get MongoDB collection for orchestrator
            mongo_client = MongoClient(os.getenv("MONGO_URI"))
            db = mongo_client[os.getenv("MONGO_DB_NAME", "mevzuat_db")]
            collection = db[os.getenv("MONGO_COLLECTION_NAME", "documents")]
            
            self.orchestrator = HybridRAGOrchestrator(
                rag_pipeline=self.rag,
                mongo_collection=collection,
                openrouter_client=self.openrouter_client
            )
            print("   ✅ Hybrid orchestrator ready")
            
        except Exception as e:
            print(f"\n❌ Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def test_query(self, query: str, expected_method: str, description: str):
        """
        Test a single query and log all steps
        
        Args:
            query: Test question
            expected_method: Expected result method (primary_rag, web_fallback, guidance)
            description: Test description
        """
        print("\n" + "─" * 100)
        print(f"🔬 TEST: {description}")
        print("─" * 100)
        print(f"📝 Query: {query}")
        print(f"🎯 Expected: {expected_method}")
        print()
        
        start_time = time.time()
        
        try:
            # Execute query
            result = self.orchestrator.query(query)
            
            elapsed = time.time() - start_time
            
            # Extract result info
            method = result.get('method', 'unknown')
            confidence = result.get('confidence', 0)
            answer = result.get('answer', '')
            sources = result.get('sources', [])
            web_sources = result.get('web_sources', [])
            fallback_reason = result.get('fallback_reason', '')
            
            # Log results
            print("\n" + "═" * 100)
            print("📊 RESULT SUMMARY")
            print("═" * 100)
            print(f"✓ Method: {method}")
            print(f"✓ Confidence: {confidence:.2f}")
            print(f"✓ Sources: {len(sources)} items")
            if web_sources:
                print(f"✓ Web Sources: {len(web_sources)} items")
            if fallback_reason:
                print(f"✓ Fallback Reason: {fallback_reason}")
            print(f"✓ Elapsed: {elapsed:.2f}s")
            
            # Check if method matches expectation
            success = (method == expected_method) or (
                expected_method == "fallback" and method in ["web_fallback", "guidance"]
            )
            
            print()
            if success:
                print(f"✅ TEST PASSED — Got expected method: {method}")
            else:
                print(f"⚠️  TEST WARNING — Expected {expected_method}, got {method}")
            
            # Log answer preview
            print("\n📄 Answer Preview (first 300 chars):")
            print("─" * 100)
            print(answer[:300] + ("..." if len(answer) > 300 else ""))
            print("─" * 100)
            
            # Log sources detail
            if sources:
                print("\n📚 Sources Detail:")
                for i, src in enumerate(sources[:3], 1):
                    if isinstance(src, dict):
                        title = src.get('title', src.get('metadata', {}).get('document_title', 'Unknown'))
                        source_type = src.get('source_type', 'document')
                        print(f"   {i}. [{source_type}] {title}")
                    else:
                        title = src.metadata.get('document_title', 'Unknown') if hasattr(src, 'metadata') else 'Unknown'
                        print(f"   {i}. [document] {title}")
            
            if web_sources:
                print("\n🌐 Web Sources Detail:")
                for i, ws in enumerate(web_sources[:3], 1):
                    url = ws.get('url', 'N/A')
                    title = ws.get('title', 'Unknown')
                    status = ws.get('status', 'unknown')
                    chunks = ws.get('chunks', 0)
                    print(f"   {i}. [{status}] {title}")
                    print(f"      URL: {url[:80]}...")
                    print(f"      Chunks: {chunks}")
            
            # Save result
            self.results.append({
                'query': query,
                'description': description,
                'expected': expected_method,
                'actual': method,
                'success': success,
                'confidence': confidence,
                'elapsed': elapsed,
                'answer_length': len(answer),
                'source_count': len(sources),
                'web_source_count': len(web_sources),
            })
            
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            self.results.append({
                'query': query,
                'description': description,
                'expected': expected_method,
                'actual': 'error',
                'success': False,
                'error': str(e),
            })
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        
        print("\n" + "=" * 100)
        print("🚀 STARTING COMPREHENSIVE TESTS")
        print("=" * 100)
        
        # ────────────────────────────────────────────
        # TEST GROUP 1: MongoDB'de VAR (RAG Success)
        # ────────────────────────────────────────────
        print("\n" + "=" * 100)
        print("📦 TEST GROUP 1: Questions that SHOULD be in MongoDB")
        print("=" * 100)
        
        self.test_query(
            query="İşverenin iş sağlığı ve güvenliği yükümlülükleri nelerdir?",
            expected_method="primary_rag",
            description="[RAG] Basic ISG obligation question"
        )
        
        self.test_query(
            query="Risk değerlendirmesi nasıl yapılır?",
            expected_method="primary_rag",
            description="[RAG] Risk assessment procedure"
        )
        
        self.test_query(
            query="İş kazası nedir ve nasıl raporlanır?",
            expected_method="primary_rag",
            description="[RAG] Work accident definition and reporting"
        )
        
        self.test_query(
            query="Kişisel koruyucu donanım kullanımı zorunlu mu?",
            expected_method="primary_rag",
            description="[RAG] Personal protective equipment requirement"
        )
        
        # ────────────────────────────────────────────
        # TEST GROUP 2: MongoDB'de YOK ama Web'de Var
        # ────────────────────────────────────────────
        print("\n" + "=" * 100)
        print("🌐 TEST GROUP 2: Questions that need WEB FALLBACK")
        print("=" * 100)
        
        self.test_query(
            query="2025 yılı asgari ücret ne kadar?",
            expected_method="fallback",  # web_fallback veya guidance
            description="[WEB] Minimum wage 2025 (not in static DB)"
        )
        
        self.test_query(
            query="Yeni çıkan İSG yönetmeliği değişiklikleri neler?",
            expected_method="fallback",
            description="[WEB] Recent ISG regulation changes"
        )
        
        self.test_query(
            query="SGK iş kazası bildirim süresi kaç gündür?",
            expected_method="fallback",
            description="[WEB] SGK accident reporting deadline (might be in web sources)"
        )
        
        # ────────────────────────────────────────────
        # TEST GROUP 3: Hiçbir Yerde YOK (Guidance)
        # ────────────────────────────────────────────
        print("\n" + "=" * 100)
        print("📋 TEST GROUP 3: Questions that should return GUIDANCE")
        print("=" * 100)
        
        self.test_query(
            query="Uzay istasyonunda çalışırken ne yapmalıyım?",
            expected_method="guidance",
            description="[GUIDANCE] Irrelevant question (space station)"
        )
        
        self.test_query(
            query="Ay'a seyahat için İSG kuralları var mı?",
            expected_method="guidance",
            description="[GUIDANCE] Nonsense question (moon travel)"
        )
        
        # ────────────────────────────────────────────
        # TEST GROUP 4: Edge Cases
        # ────────────────────────────────────────────
        print("\n" + "=" * 100)
        print("🔬 TEST GROUP 4: EDGE CASES")
        print("=" * 100)
        
        self.test_query(
            query="iş güvenliği",
            expected_method="primary_rag",
            description="[EDGE] Very short query"
        )
        
        self.test_query(
            query="İşyerinde yangın söndürme cihazlarının yerleştirilmesi, bakımı ve kontrolü ile ilgili düzenlemeler nelerdir ve işveren bu konuda hangi yükümlülüklere sahiptir?",
            expected_method="primary_rag",
            description="[EDGE] Very long detailed query"
        )
        
        self.test_query(
            query="KKD zorunlu mu",
            expected_method="primary_rag",
            description="[EDGE] Abbreviation + informal language"
        )
    
    def print_final_report(self):
        """Print comprehensive test report"""
        
        total_elapsed = (datetime.now() - self.test_start).total_seconds()
        
        print("\n" + "=" * 100)
        print("📊 FINAL TEST REPORT")
        print("=" * 100)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get('success', False))
        failed = total - passed
        
        print(f"\n✓ Total Tests: {total}")
        print(f"✓ Passed: {passed} ({100*passed/total:.1f}%)")
        print(f"✓ Failed: {failed} ({100*failed/total:.1f}%)")
        print(f"✓ Total Time: {total_elapsed:.2f}s")
        print(f"✓ Avg Time: {total_elapsed/total:.2f}s per test")
        
        # Method breakdown
        methods = {}
        for r in self.results:
            method = r.get('actual', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        
        print("\n📈 Method Distribution:")
        for method, count in sorted(methods.items(), key=lambda x: -x[1]):
            print(f"   • {method}: {count} ({100*count/total:.1f}%)")
        
        # Failed tests detail
        if failed > 0:
            print("\n⚠️  Failed Tests Detail:")
            for r in self.results:
                if not r.get('success', False):
                    print(f"\n   ❌ {r['description']}")
                    print(f"      Query: {r['query'][:60]}...")
                    print(f"      Expected: {r['expected']}")
                    print(f"      Got: {r.get('actual', 'error')}")
                    if 'error' in r:
                        print(f"      Error: {r['error']}")
        
        # Performance stats
        avg_confidence = sum(r.get('confidence', 0) for r in self.results) / total
        avg_answer_length = sum(r.get('answer_length', 0) for r in self.results) / total
        
        print("\n📊 Performance Stats:")
        print(f"   • Avg Confidence: {avg_confidence:.2f}")
        print(f"   • Avg Answer Length: {avg_answer_length:.0f} chars")
        
        # Orchestrator stats
        print("\n📊 Orchestrator Statistics:")
        self.orchestrator.print_statistics()
        
        print("\n" + "=" * 100)
        print("✅ TEST SUITE COMPLETE")
        print("=" * 100)


if __name__ == "__main__":
    # Run tests
    tester = WorkflowTester()
    tester.run_all_tests()
    tester.print_final_report()
