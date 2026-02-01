"""
Quick RAGAS Evaluation Test

RAGAS'ı test etmek için basit script.
Tam evaluation yerine 2-3 soruyla hızlı test yapar.

Kullanım:
    python test_ragas_quick.py
"""

import os
import sys

print("=" * 70)
print("🧪 RAGAS Quick Test")
print("=" * 70)

# Check RAGAS availability
print("\n1️⃣  RAGAS kütüphanesi kontrol ediliyor...")
try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy
    from datasets import Dataset
    print("   ✅ RAGAS yüklü")
except ImportError as e:
    print(f"   ❌ RAGAS yüklü değil: {e}")
    print("\n📦 Yüklemek için:")
    print("   pip install ragas datasets")
    sys.exit(1)

# Check MongoDB connection
print("\n2️⃣  MongoDB bağlantısı kontrol ediliyor...")
try:
    from mongodb_vector_store import get_mongodb_vectorstore
    vectorstore = get_mongodb_vectorstore()
    stats = vectorstore.get_collection_stats()
    print(f"   ✅ MongoDB bağlı - {stats['count']} döküman bulundu")
except Exception as e:
    print(f"   ❌ MongoDB bağlantı hatası: {e}")
    sys.exit(1)

# Check RAG components
print("\n3️⃣  RAG bileşenleri kontrol ediliyor...")
try:
    from client import create_openrouter_client
    from reranker import RerankerService
    from rag_pipeline import RAGPipeline
    
    client = create_openrouter_client()
    reranker = RerankerService()
    rag = RAGPipeline(client, vectorstore, reranker)
    print("   ✅ RAG pipeline hazır")
except Exception as e:
    print(f"   ❌ RAG initialization hatası: {e}")
    sys.exit(1)

# Run quick test with 2 questions
print("\n4️⃣  Hızlı test çalıştırılıyor (2 soru)...")
print("-" * 70)

questions = [
    "İşverenin iş sağlığı ve güvenliği konusundaki yükümlülükleri nelerdir?",
    "Risk değerlendirmesi nedir?"
]

ground_truths = [
    "İşveren, çalışanların iş sağlığı ve güvenliğini sağlamakla yükümlüdür.",
    "Risk değerlendirmesi, işyerinde var olan tehlikelerin belirlenmesi çalışmalarıdır."
]

answers = []
contexts = []

for i, question in enumerate(questions, 1):
    print(f"\n[{i}/2] Soru: {question[:60]}...")
    try:
        # Get answer
        response = rag.generate_response(question)
        answer = response.split("═" * 70)[0].strip()
        
        # Get context (retrieve again for simplicity)
        from query_expansion import expand_query
        search_query = expand_query(client, question)
        initial_docs = vectorstore.similarity_search(search_query, k=20)
        relevant_docs = reranker.rerank_documents(search_query, initial_docs)
        context_list = [doc.page_content for doc in relevant_docs[:3]]
        
        answers.append(answer)
        contexts.append(context_list)
        
        print(f"    ✓ Cevap alındı ({len(answer)} karakter)")
        print(f"    ✓ Context: {len(context_list)} döküman")
        
    except Exception as e:
        print(f"    ❌ Hata: {e}")
        sys.exit(1)

# Create dataset
print("\n5️⃣  RAGAS dataset oluşturuluyor...")
data = {
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "ground_truth": ground_truths
}

dataset = Dataset.from_dict(data)
print("   ✅ Dataset hazır")

# Run RAGAS evaluation
print("\n6️⃣  RAGAS metrikleri hesaplanıyor...")
print("    (Bu 1-2 dakika sürebilir...)")

try:
    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy
        ]
    )
    
    print("\n" + "=" * 70)
    print("✅ TEST BAŞARILI!")
    print("=" * 70)
    
    print("\n📊 Metrik Sonuçları:\n")
    print(f"   Faithfulness (Sadakat):       {result['faithfulness']:.3f}")
    print(f"   Answer Relevancy (İlgililik): {result['answer_relevancy']:.3f}")
    
    print("\n💡 Tam evaluation için:")
    print("   python ragas_evaluation.py")
    
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"\n❌ Evaluation hatası: {e}")
    print("\n🔍 Debug bilgisi:")
    print(f"   Questions: {len(questions)}")
    print(f"   Answers: {len(answers)}")
    print(f"   Contexts: {len(contexts)}")
    print(f"   Ground truths: {len(ground_truths)}")
    sys.exit(1)
