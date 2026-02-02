"""
Main RAG pipeline with intelligent memory management and metadata-driven grounding.
"""

from config import (
    MODEL_NAME,
    TEMPERATURE,
    MAX_TOKENS,
    INITIAL_RETRIEVAL_K,
    TOP_RERANKED_K,
    MAX_CONVERSATION_HISTORY,
    MEMORY_STRATEGY
)
from query_expansion import expand_query, analyze_query_context, build_metadata_filter


class RAGPipeline:
    """Main RAG Pipeline for Law 6331 Q&A with Smart Memory and Metadata-Injection"""
    
    def __init__(self, client, vectorstore, reranker, max_history=None):
        self.client = client
        self.vectorstore = vectorstore
        self.reranker = reranker
        self.conversation_history = []
        self.max_history = max_history or MAX_CONVERSATION_HISTORY
        self.memory_strategy = MEMORY_STRATEGY
    
    def _manage_conversation_memory(self):
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def _format_sources(self, documents):
        if not documents:
            return ""
        
        sources = "\n\n" + "═" * 70 + "\n"
        sources += "📚 CEVABINIZ İÇİN KULLANILAN KAYNAKLAR\n"
        sources += "═" * 70 + "\n\n"
        
        for idx, doc in enumerate(documents, 1):
            document_title = doc.metadata.get('document_title', 'Bilinmeyen Belge')
            madde_number = doc.metadata.get('madde_number', 'Bilinmeyen')
            full_reference = doc.metadata.get('full_reference', document_title)
            document_type = doc.metadata.get('document_type', '')
            page = doc.metadata.get('page', 'N/A')
            
            sources += f"📄 Kaynak {idx}: {full_reference}\n"
            sources += "─" * 70 + "\n"
            
            if document_type:
                category = "📜 Kanun/Yönetmelik" if "KANUN" in document_type else "📋 Tebliğ"
                sources += f"{category}\n"
            
            if madde_number != "Bilinmeyen":
                sources += f"📌 MADDE: {madde_number}\n"
            
            sources += f"📖 Sayfa: {page}\n"
            
            content_preview = doc.page_content[:200].replace('\n', ' ').strip()
            sources += f"💬 Alıntı: \"{content_preview}...\"\n\n"
        
        sources += "═" * 70 + "\n"
        sources += "💡 Not: Kaynaklar MADDE bazlı parçalama ile hassas şekilde seçilmiştir.\n"
        return sources
    
    def generate_response(self, user_input):
        """
        Gelişmiş RAG Pipeline: Metadata Zenginleştirme ve Sektörel Filtreleme
        """
        # Step 1 & 2: Akıllı Filtreleme
        print("\n🧠 Bağlam analizi ve akıllı filtreleme yapılıyor...")
        query_analysis = analyze_query_context(self.client, user_input)
        metadata_filter = build_metadata_filter(query_analysis)
        
        # Step 3 & 4: Retrieval (Sektörel filtre uygulanmış şekilde)
        search_query = user_input 
        print(f"📚 MongoDB üzerinden belgeler getiriliyor...")
        initial_docs = self.vectorstore.similarity_search(
            search_query,
            k=INITIAL_RETRIEVAL_K,
            filter_dict=metadata_filter
        )
        
        # Fallback: Eğer filtre çok darsa ve sonuç gelmediyse filtresiz dene
        if not initial_docs:
            print("⚠️ Belirlenen filtre ile belge bulunamadı, genel arama yapılıyor...")
            initial_docs = self.vectorstore.similarity_search(search_query, k=INITIAL_RETRIEVAL_K, filter_dict=None)

        # Step 5: Reranking (Voyage AI)
        if self.reranker and initial_docs:
            print(f"🎯 {len(initial_docs)} belge rerank ediliyor...")
            relevant_docs = self.reranker.rerank_documents(search_query, initial_docs, top_k=TOP_RERANKED_K)
        else:
            relevant_docs = initial_docs[:TOP_RERANKED_K]

        # 🔥 YENİ ADIM 6: CONTEXT ENRICHMENT (Metadata Injection)
        # LLM'in her parçanın hangi dökümana ve maddeye ait olduğunu kesin görmesini sağlıyoruz.
        enriched_context_list = []
        for doc in relevant_docs:
            title = doc.metadata.get('document_title', 'Bilinmeyen Yönetmelik')
            madde = doc.metadata.get('madde_number', 'Bilinmeyen Madde')
            ref = doc.metadata.get('full_reference', title)
            
            # Metadata'yı metnin tepesine 'Inject' ediyoruz ki LLM uydurmasın.
            context_chunk = f"--- KAYNAK: {ref} | MADDE: {madde} ---\nİÇERİK: {doc.page_content}\n"
            enriched_context_list.append(context_chunk)
        
        context = "\n\n".join(enriched_context_list)

        # 🔥 YENİ ADIM 7: STRICT GROUNDING PROMPT (Sıkı Sadakat)
        rag_prompt = f"""Sen uzman bir İSG Mevzuat Danışmanısın. Aşağıdaki kurallara KESİNLİKLE uy:

TALİMATLAR:
1. SADECE aşağıda sunulan 'Mevzuat Metinleri'ndeki bilgileri kullan.
2. Eğer cevap bu metinlerde YOKSA, "Bu bilgi mevcut mevzuat kaynaklarında bulunamadı." de ve dışarıdan asla bilgi uydurma.
3. Her bilginin sonuna hangi Yönetmelik ve Madde'den alındığını parantez içinde yaz (Örn: Yapı İşleri Yönetmeliği Madde 5).
4. Kaynaklar arasında sektör uyuşmazlığı varsa (Örn: Soru inşaat, kaynak maden) bunu belirt.
5. "Unknown" veya "Bilinmeyen" ifadesini kullanma, başlık metadatasını baz al.

Mevzuat Metinleri:
{context}

Soru: {user_input}

Yanıt (Profesyonel, Net ve Madde Bazlı):"""

        self.conversation_history.append({"role": "user", "content": user_input})
        self._manage_conversation_memory()

        messages = [
            {"role": "system", "content": "Sen Türk İş Sağlığı ve Güvenliği mevzuatı konusunda uzman, sadece kanıtlara dayanan bir danışmansın."}
        ] + self.conversation_history[:-1] + [
            {"role": "user", "content": rag_prompt}
        ]

        # Step 8: Yanıt Üretimi (Düşük Temperature ile)
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.1, # Kesinlik için sıcaklığı düşürdük
            max_tokens=MAX_TOKENS
        )
        
        response_text = response.choices[0].message.content
        sources_footer = self._format_sources(relevant_docs)
        
        self.conversation_history.append({"role": "assistant", "content": response_text})
        self._manage_conversation_memory()

        return response_text + sources_footer

    def reset_conversation(self):
        self.conversation_history = []
