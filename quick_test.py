#!/usr/bin/env python3
"""
Quick RAG System Test - MongoDB ve MADDE metadata kontrolü
"""

from rag_pipeline import RAGPipeline
import json

print('🧪 RAG Sistemi Hızlı Test')
print('=' * 80)

# Pipeline başlat
print('\n🚀 RAG Pipeline başlatılıyor...')
rag = RAGPipeline()
print('✅ Pipeline hazır!')

# Test soruları
test_questions = [
    'İş güvenliği uzmanlarının çalışma süreleri nedir?',
    'Risk değerlendirmesi nasıl yapılır?',
    'KKD maliyeti kime aittir?',
]

results = []

for i, question in enumerate(test_questions, 1):
    print(f'\n{"=" * 80}')
    print(f'📝 TEST {i}/{len(test_questions)}')
    print(f'❓ Soru: {question}')
    print('-' * 80)
    
    try:
        result = rag.query(question)
        
        print(f'✅ Yanıt alındı!')
        
        # Chunk sayısı
        chunks = result.get('retrieved_chunks', [])
        print(f'📊 Alınan chunk sayısı: {len(chunks)}')
        
        # Metadata kontrolü
        if chunks:
            print(f'\n📌 İlk 3 Chunk Metadata:')
            for idx, chunk in enumerate(chunks[:3], 1):
                metadata = chunk.get('metadata', {})
                print(f'\n   Chunk {idx}:')
                print(f'   - Döküman: {metadata.get("document_title", "YOK")[:50]}...')
                print(f'   - MADDE: {metadata.get("madde_number", "YOK")}')
                print(f'   - Tam MADDE: {metadata.get("is_complete_madde", False)}')
                print(f'   - FIKRA: {metadata.get("has_fikra", False)}')
                print(f'   - Referans: {metadata.get("full_reference", "YOK")[:60]}...')
        
        # Yanıt
        answer = result.get('answer', '')
        print(f'\n💬 Yanıt ({len(answer)} karakter):')
        print(f'{answer[:300]}...')
        
        results.append({
            'question': question,
            'success': True,
            'chunks_count': len(chunks),
            'answer_length': len(answer)
        })
        
    except Exception as e:
        print(f'❌ HATA: {str(e)}')
        results.append({
            'question': question,
            'success': False,
            'error': str(e)
        })

print('\n' + '=' * 80)
print('📊 TEST SONUÇLARI:')
print('=' * 80)

success_count = sum(1 for r in results if r.get('success'))
print(f'✅ Başarılı: {success_count}/{len(results)}')
print(f'❌ Başarısız: {len(results) - success_count}/{len(results)}')

if success_count > 0:
    avg_chunks = sum(r.get('chunks_count', 0) for r in results if r.get('success')) / success_count
    print(f'📊 Ortalama chunk sayısı: {avg_chunks:.1f}')

print('\n✅ Test tamamlandı!')
