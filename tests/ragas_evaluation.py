"""
RAGAS Evaluation Framework for Legislation RAG System

Bu script RAG sisteminin kalitesini ölçer:
- Faithfulness (Sadakat): Cevap kaynağa ne kadar sadık?
- Answer Relevancy (İlgililik): Cevap soruya ne kadar uygun?
- Context Precision (Bağlam Hassasiyeti): Doğru dökümanlar mı alındı?
- Context Recall (Bağlam Hatırlama): Tüm ilgili bilgi bulundu mu?

Kullanım:
    python ragas_evaluation.py
"""

import os
import json
from datetime import datetime
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

# RAGAS imports
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
        context_relevancy
    )
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    print("⚠️  RAGAS kurulu değil. Lütfen yükleyin: pip install ragas")
    RAGAS_AVAILABLE = False

# Local imports
from mongodb_vector_store import get_mongodb_vectorstore
from client import create_openrouter_client
from reranker import RerankerService
from rag_pipeline import RAGPipeline


class RAGEvaluator:
    """RAGAS-based RAG system evaluator"""
    
    def __init__(self, output_dir="./evaluation_results"):
        """
        Initialize evaluator
        
        Args:
            output_dir: Directory to save evaluation results
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize RAG components
        print("🚀 RAG sistemini başlatıyorum...")
        self.client = create_openrouter_client()
        self.vectorstore = get_mongodb_vectorstore()
        self.reranker = RerankerService()
        self.rag_pipeline = RAGPipeline(self.client, self.vectorstore, self.reranker)
        print("✅ RAG sistemi hazır!\n")
    
    def create_test_dataset(self) -> List[Dict]:
        """
        Create test dataset with questions and ground truth
        
        Returns:
            List of test cases
        """
        # Test soruları (gerçek kullanım senaryoları)
        test_cases = [
            {
                "question": "İşverenin iş sağlığı ve güvenliği konusundaki yükümlülükleri nelerdir?",
                "ground_truth": "İşveren, çalışanların iş sağlığı ve güvenliğini sağlamakla yükümlüdür. Risk değerlendirmesi yapmak, gerekli önlemleri almak, çalışanları bilgilendirmek ve eğitmek zorundadır."
            },
            {
                "question": "Risk değerlendirmesi nedir ve nasıl yapılır?",
                "ground_truth": "Risk değerlendirmesi, işyerinde var olan ya da dışarıdan gelebilecek tehlikelerin belirlenmesi, bu tehlikelerin riske dönüşmesine yol açan faktörler ile tehlikelerden kaynaklanan risklerin analiz edilerek derecelendirilmesi ve kontrol tedbirlerinin kararlaştırılması çalışmalarıdır."
            },
            {
                "question": "İş güvenliği uzmanı görevlendirmesi zorunlu mudur?",
                "ground_truth": "İşveren, işyerlerinde iş sağlığı ve güvenliği hizmetlerini yürütmek üzere iş güvenliği uzmanı görevlendirmek zorundadır. Bu zorunluluk işyerinin tehlike sınıfına ve çalışan sayısına göre değişir."
            },
            {
                "question": "Çalışan temsilcisi kimdir ve nasıl seçilir?",
                "ground_truth": "Çalışan temsilcisi, iş sağlığı ve güvenliği konularında işveren ile çalışanlar arasında koordinasyonu sağlayan, çalışanlar tarafından seçilen kişidir. En az elli çalışanı olan işyerlerinde çalışan temsilcisi bulundurulur."
            },
            {
                "question": "Kişisel koruyucu donanım kullanımı zorunlu mudur?",
                "ground_truth": "İşveren, çalışma ortamında sağlık ve güvenlik risklerinin mühendislik tedbirleri ve diğer yöntemlerle önlenemediği veya tam olarak sınırlandırılamadığı durumlarda uygun kişisel koruyucu donanımları sağlamak ve kullandırmak zorundadır."
            }
        ]
        
        return test_cases
    
    def run_evaluation(self, test_cases: List[Dict]) -> Dict:
        """
        Run RAGAS evaluation on test cases
        
        Args:
            test_cases: List of test questions and ground truths
            
        Returns:
            Evaluation results
        """
        if not RAGAS_AVAILABLE:
            print("❌ RAGAS yüklü değil!")
            return {}
        
        print("=" * 70)
        print("🧪 RAGAS Evaluation Başlıyor")
        print("=" * 70)
        
        # Prepare data for RAGAS
        questions = []
        answers = []
        contexts = []
        ground_truths = []
        
        print(f"\n📝 {len(test_cases)} test sorusu işleniyor...\n")
        
        for i, test_case in enumerate(test_cases, 1):
            question = test_case["question"]
            ground_truth = test_case["ground_truth"]
            
            print(f"[{i}/{len(test_cases)}] Soru: {question[:60]}...")
            
            # Get RAG response
            try:
                # Get answer from RAG pipeline
                full_response = self.rag_pipeline.generate_response(question)
                
                # Extract answer (remove sources section)
                answer = full_response.split("═" * 70)[0].strip()
                
                # Get context from last retrieval
                # We need to access the documents used
                # For now, we'll retrieve again for context
                from query_expansion import expand_query
                search_query = expand_query(self.client, question)
                initial_docs = self.vectorstore.similarity_search(search_query, k=50)
                relevant_docs = self.reranker.rerank_documents(search_query, initial_docs)
                
                # Context is the retrieved documents
                context_list = [doc.page_content for doc in relevant_docs[:5]]
                
                questions.append(question)
                answers.append(answer)
                contexts.append(context_list)
                ground_truths.append(ground_truth)
                
                print(f"    ✓ Cevap alındı ({len(answer)} karakter)")
                print(f"    ✓ Context: {len(context_list)} döküman\n")
                
            except Exception as e:
                print(f"    ❌ Hata: {e}\n")
                continue
        
        # Create RAGAS dataset
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths
        }
        
        dataset = Dataset.from_dict(data)
        
        print("\n" + "=" * 70)
        print("📊 RAGAS Metrikleri Hesaplanıyor...")
        print("=" * 70)
        
        # Run evaluation
        try:
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,          # Sadakat: Cevap kaynaklara ne kadar sadık?
                    answer_relevancy,      # İlgililik: Cevap soruya ne kadar uygun?
                    context_precision,     # Hassasiyet: Doğru dökümanlar mı alındı?
                    context_recall,        # Hatırlama: Tüm ilgili bilgi bulundu mu?
                    context_relevancy      # Bağlam İlgililikliliği
                ]
            )
            
            return result
            
        except Exception as e:
            print(f"❌ Evaluation hatası: {e}")
            return {}
    
    def save_results(self, results: Dict, test_cases: List[Dict]):
        """
        Save evaluation results to file
        
        Args:
            results: RAGAS evaluation results
            test_cases: Original test cases
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ragas_evaluation_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Prepare output
        output = {
            "timestamp": timestamp,
            "date": datetime.now().isoformat(),
            "num_test_cases": len(test_cases),
            "metrics": {
                "faithfulness": float(results.get("faithfulness", 0)),
                "answer_relevancy": float(results.get("answer_relevancy", 0)),
                "context_precision": float(results.get("context_precision", 0)),
                "context_recall": float(results.get("context_recall", 0)),
                "context_relevancy": float(results.get("context_relevancy", 0))
            },
            "test_cases": test_cases
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Sonuçlar kaydedildi: {filepath}")
        
        return filepath
    
    def print_report(self, results: Dict):
        """
        Print evaluation report
        
        Args:
            results: RAGAS evaluation results
        """
        print("\n" + "=" * 70)
        print("📊 RAGAS EVALUATION RAPORU")
        print("=" * 70)
        
        metrics = {
            "Faithfulness (Sadakat)": results.get("faithfulness", 0),
            "Answer Relevancy (İlgililik)": results.get("answer_relevancy", 0),
            "Context Precision (Hassasiyet)": results.get("context_precision", 0),
            "Context Recall (Hatırlama)": results.get("context_recall", 0),
            "Context Relevancy (Bağlam İlgililkliliği)": results.get("context_relevancy", 0)
        }
        
        print("\n📈 Metrik Skorları (0-1 arası, 1 en iyi):\n")
        
        for metric_name, score in metrics.items():
            # Visual bar
            bar_length = int(score * 40)
            bar = "█" * bar_length + "░" * (40 - bar_length)
            
            # Rating
            if score >= 0.8:
                rating = "🟢 Mükemmel"
            elif score >= 0.6:
                rating = "🟡 İyi"
            elif score >= 0.4:
                rating = "🟠 Orta"
            else:
                rating = "🔴 Düşük"
            
            print(f"{metric_name:40s}: {score:.3f} {bar} {rating}")
        
        # Overall score
        avg_score = sum(metrics.values()) / len(metrics)
        print("\n" + "-" * 70)
        print(f"{'GENEL ORTALAMA':40s}: {avg_score:.3f}")
        print("-" * 70)
        
        # Interpretation
        print("\n💡 Metrik Açıklamaları:\n")
        print("  • Faithfulness: Cevabın kaynaklara ne kadar sadık olduğu")
        print("  • Answer Relevancy: Cevabın soruyla ne kadar ilgili olduğu")
        print("  • Context Precision: Alınan dökümanların ne kadar doğru olduğu")
        print("  • Context Recall: Tüm ilgili bilginin bulunup bulunmadığı")
        print("  • Context Relevancy: Bağlamın soruyla ne kadar ilgili olduğu")
        
        # Recommendations
        print("\n🎯 Öneriler:\n")
        
        if metrics["Faithfulness (Sadakat)"] < 0.7:
            print("  ⚠️  Faithfulness düşük - LLM hallucination yapıyor olabilir")
            print("      → Prompt'u daha kısıtlayıcı hale getirin")
            print("      → \"ONLY use the information provided\" talimatını güçlendirin")
        
        if metrics["Answer Relevancy (İlgililik)"] < 0.7:
            print("  ⚠️  Answer Relevancy düşük - Cevaplar konudan sapıyor")
            print("      → Query expansion stratejisini gözden geçirin")
            print("      → LLM prompt'unu daha spesifik yapın")
        
        if metrics["Context Precision (Hassasiyet)"] < 0.7:
            print("  ⚠️  Context Precision düşük - Yanlış dökümanlar alınıyor")
            print("      → Reranker modelini iyileştirin")
            print("      → Embedding modelini fine-tune edin")
        
        if metrics["Context Recall (Hatırlama)"] < 0.7:
            print("  ⚠️  Context Recall düşük - Bazı ilgili bilgiler kaçırılıyor")
            print("      → INITIAL_RETRIEVAL_K değerini artırın")
            print("      → Vector search parametrelerini optimize edin")
        
        print("\n" + "=" * 70)


def main():
    """Main evaluation function"""
    
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "RAGAS EVALUATION SYSTEM" + " " * 25 + "║")
    print("╚" + "═" * 68 + "╝\n")
    
    if not RAGAS_AVAILABLE:
        print("❌ RAGAS kütüphanesi yüklü değil!")
        print("\n📦 Yüklemek için:")
        print("   pip install ragas")
        return
    
    # Initialize evaluator
    evaluator = RAGEvaluator()
    
    # Create test dataset
    print("📝 Test dataset'i hazırlanıyor...")
    test_cases = evaluator.create_test_dataset()
    print(f"✅ {len(test_cases)} test sorusu hazır\n")
    
    # Run evaluation
    results = evaluator.run_evaluation(test_cases)
    
    if results:
        # Print report
        evaluator.print_report(results)
        
        # Save results
        evaluator.save_results(results, test_cases)
        
        print("\n✅ Evaluation tamamlandı!")
    else:
        print("\n❌ Evaluation başarısız!")


if __name__ == "__main__":
    main()
