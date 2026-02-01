"""
Test script for beautiful source formatting
"""

def test_source_formatting():
    """Test the new source formatting"""
    
    print("=" * 70)
    print("📚 Kaynak Gösterimi Test")
    print("=" * 70)
    
    # Mock document class
    class MockDoc:
        def __init__(self, content, source_file, page, page_label, source_dir):
            self.page_content = content
            self.metadata = {
                'source_file': source_file,
                'page': page,
                'page_label': page_label,
                'source_dir': source_dir
            }
    
    # Create mock documents
    documents = [
        MockDoc(
            "Madde 4 - İşveren, çalışanların iş sağlığı ve güvenliğini sağlamakla yükümlüdür. Bu kapsamda risk değerlendirmesi yapmak, gerekli önlemleri almak zorundadır.",
            "İŞ SAĞLIĞI VE GÜVENLİĞİ KANUNU.pdf",
            3,
            "4",
            "KANUN VE YÖNETMELİKLER"
        ),
        MockDoc(
            "Madde 10 - İşyerlerinde iş sağlığı ve güvenliği hizmetlerini yürütmek üzere işveren tarafından iş güvenliği uzmanı görevlendirilir.",
            "İŞ SAĞLIĞI VE GÜVENLİĞİ KANUNU.pdf",
            9,
            "10",
            "KANUN VE YÖNETMELİKLER"
        ),
        MockDoc(
            "Risk değerlendirmesi, işyerinde var olan ya da dışarıdan gelebilecek tehlikelerin belirlenmesi, bu tehlikelerin riske dönüşmesine yol açan faktörler ile tehlikelerden kaynaklanan risklerin analiz edilerek derecelendirilmesi",
            "İŞ SAĞLIĞI VE GÜVENLİĞİ RİSK DEĞERLENDİRMESİ YÖNETMELİĞİ.pdf",
            2,
            "3",
            "KANUN VE YÖNETMELİKLER"
        ),
        MockDoc(
            "İşyerlerinde tehlike sınıfları belirleme rehberine dair tebliğ ile işyerleri tehlike sınıflarına göre gruplandırılır.",
            "İŞ SAĞLIĞI VE GÜVENLİĞİNE İLİŞKİN İŞYERİ TEHLİKE SINIFLARI TEBLİĞİ.pdf",
            1,
            "2",
            "TEBLİĞ"
        )
    ]
    
    # Import the formatting function
    import sys
    sys.path.insert(0, '/Users/selcuk/Desktop/admin_pan/Legislation_RAG')
    from rag_pipeline import RAGPipeline
    
    # Create a mock pipeline instance
    class MockClient:
        pass
    
    class MockVectorStore:
        pass
    
    class MockReranker:
        pass
    
    pipeline = RAGPipeline(
        client=MockClient(),
        vectorstore=MockVectorStore(),
        reranker=MockReranker()
    )
    
    # Test the formatting
    formatted_sources = pipeline._format_sources(documents)
    
    print("\n" + formatted_sources)
    
    print("\n" + "=" * 70)
    print("✅ Kaynak formatı test edildi!")
    print("=" * 70)
    
    # Show stats
    print(f"\n📊 İstatistikler:")
    print(f"  • Toplam kaynak döküman: {len(documents)}")
    unique_sources = len(set(doc.metadata['source_file'] for doc in documents))
    print(f"  • Benzersiz dosya: {unique_sources}")
    print(f"  • Formatlanmış metin uzunluğu: {len(formatted_sources)} karakter")


if __name__ == "__main__":
    test_source_formatting()
