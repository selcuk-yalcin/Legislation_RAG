"""
Main RAG pipeline with intelligent memory management
Optimized for Voyage Law-2 & GPT-4o-mini
"""

from config import (
    MODEL_NAME,
    TEMPERATURE,
    MAX_TOKENS,
    INITIAL_RETRIEVAL_K, # Bu değer config.py'de 100 olmalı
    TOP_RERANKED_K,
    MAX_CONVERSATION_HISTORY,
    MEMORY_STRATEGY
)
from query_expansion import expand_query, analyze_query_context, build_metadata_filter


class RAGPipeline:
    """Main RAG Pipeline for Law 6331 Q&A with Smart Memory and Structural Precision"""
    
    def __init__(self, client, vectorstore, reranker, max_history=None):
        """Initialize RAG Pipeline with enhanced components"""
        self.client = client
        self.vectorstore = vectorstore
        self.reranker = reranker
        self.conversation_history = []
        self.max_history = max_history or MAX_CONVERSATION_HISTORY
        self.memory_strategy = MEMORY_STRATEGY
    
    def _manage_conversation_memory(self):
        """Intelligent conversation memory management to prevent context overflow"""
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def _format_sources(self, documents):
        """Format source documents with MADDE-level precision metadata"""
        if not documents:
            return ""
        
        sources = "\n\n" + "═" * 70 + "\n"
        sources += "📚 CEVABINIZ İÇİN KULLANILAN KAYNAKLAR\n"
        sources += "═" * 70 + "\n\n"
        
        for idx, doc in enumerate(documents, 1):
            document_title = doc.metadata.get('document_title', doc.metadata.get('source_file', 'Bilinmeyen Belge'))
            madde_number = doc.metadata.get('madde_number', 'Bilinmeyen')
            page = doc.metadata.get('page', 'N/A')
            
            sources += f"📄 Kaynak {idx}: {document_title}\n"
            sources += "─" * 70 + "\n"
            
            if madde_number != "Bilinmeyen":
                sources += f"📌 MADDE: {madde_number}\n"
            
            sources += f"📖 Sayfa: {page}\n"
            
            # İçerik önizleme - tam madde göster (2000 karakter)
            content_preview = doc.page_content[:2000].replace('\n', ' ').strip()
            sources += f"💬 Alıntı: \"{content_preview}\"\n\n"
        
        sources += "═" * 70 + "\n"
        sources += "💡 Not: Kaynaklar MADDE bazlı parçalama ile hassas şekilde seçilmiştir.\n"
        return sources
    
    def generate_response(self, user_input):
        """
        Main RAG Pipeline Optimized:
        1. Context Analysis -> 2. Metadata Filtering -> 3. Broad Retrieval (K=100)
        4. Voyage Reranking -> 5. Hardened Prompt Generation
        """
        # Step 1 & 2: Akıllı Filtreleme (Gemi/Maden ayrımı için)
        print(f"\n🧠 Analiz ediliyor: '{user_input[:50]}...'")
        query_analysis = analyze_query_context(self.client, user_input)
        metadata_filter = build_metadata_filter(query_analysis)
        
        # Step 3: Geniş Arama (INITIAL_RETRIEVAL_K = 100 olmalı)
        print(f"📚 MongoDB'den {INITIAL_RETRIEVAL_K} aday döküman getiriliyor...")
        initial_docs = self.vectorstore.similarity_search(
            user_input,
            k=INITIAL_RETRIEVAL_K,
            filter_dict=metadata_filter
        )
        
        # Step 4: Voyage Reranker ile Nokta Atışı
        if self.reranker and initial_docs:
            print(f"🎯 Voyage Reranker {len(initial_docs)} dökümanı sıralıyor...")
            relevant_docs = self.reranker.rerank_documents(user_input, initial_docs, top_k=TOP_RERANKED_K)
        else:
            relevant_docs = initial_docs[:TOP_RERANKED_K]
        
        # Step 5: Bağlam Oluşturma
        context = "\n\n".join([f"KAYNAK [{doc.metadata.get('source_file')}]: {doc.page_content}" for doc in relevant_docs])
        
        # Step 6: Sertleştirilmiş Prompt (Hallucination Engelleyici)
        # OLD VERSION - Keeping for reference
        # rag_prompt = f"""
        # Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış, son derece titiz bir hukuk danışmanısın. 
        # Görevin, aşağıdaki 'Mevzuat İçeriği' kısmını bir hakim hassasiyetiyle incelemek ve soruyu yanıtlamaktır.
        # ...
        # """
        
        # NEW VERSION - Simplified format without MADDE numbers (temporary fix)
        rag_prompt = f"""
Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış bir danışmansın.

YANIT FORMATI:
- Her önemli nokta için başlık kullan (bold formatında: **Başlık:**)
- Kaynak referanslarını köşeli parantez içinde SADECE yönetmelik/kanun adı olarak yaz
- Dosya adı (.pdf) kullanma, sadece resmi yönetmelik/kanun adını yaz
- MADDE numarası KULLANMA
- Temiz, okunaklı ve madde işaretli liste formatında yanıt ver

ÖRNEK FORMAT:
**Acil Durumların Belirlenmesi:** İşyerinde meydana gelebilecek acil durumlar, tasarım veya kuruluş aşamasından itibaren belirlenmelidir. [İşyerlerinde Acil Durumlar Hakkında Yönetmelik]

**Önleyici Tedbirler:** Belirlenen acil durumların olumsuz etkilerini önleyici tedbirler alınmalıdır. [İşyerlerinde Acil Durumlar Hakkında Yönetmelik]

KAYNAK İSİMLENDİRME KURALLARI:
- "İŞ SAĞLIĞI VE GÜVENLİĞİ RİSK DEĞERLENDİRMESİ YÖNETMELİĞİ.pdf" yerine → [İş Sağlığı ve Güvenliği Risk Değerlendirmesi Yönetmeliği]
- "6331_SAYILI_KANUN.pdf" yerine → [6331 Sayılı İş Sağlığı ve Güvenliği Kanunu]
- Her zaman düzgün Türkçe başlık formatında yaz (ilk harf büyük, geri kalan küçük)
- .pdf uzantısı ASLA yazma

KURALLAR:
1. SADECE aşağıdaki mevzuat içeriğine dayan
2. Her bilginin sonuna kaynak referansı ekle
3. Bilgi yoksa: "Sağlanan kaynaklarda bu konuya dair bilgi bulunamamıştır" de
4. Spekülatif ifadeler kullanma
5. MADDE numarası yazma

Mevzuat İçeriği:
----------------------------------
{context}
----------------------------------

Kullanıcı Sorusu: {user_input}

Yanıt (Temiz, Kaynaklı ve Başlıklı Format):"""
        
        # Mesaj Geçmişi Yönetimi
        messages = [
            {
                "role": "system",
                # "content": "Sen, sadece sağlanan metinleri kullanarak cevap veren, yorum katmayan ve hukuki dökümanlara %100 sadık kalan bir Türk Mevzuat Analiz Sistemisin."
                "content": "Sen İSG mevzuatı danışmanısın. Yanıtlarını **Başlık:** formatında ver ve kaynak referanslarını [Yönetmelik Adı] şeklinde ekle. Dosya adı (.pdf) ve MADDE numarası kullanma. Sadece sağlanan metinlere dayan."
            }
        ] + self.conversation_history + [
            {"role": "user", "content": rag_prompt}
        ]
        
        # Step 7: Cevap Üretimi (GPT-4o-mini)
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        response_text = response.choices[0].message.content
        sources_html = self._format_sources(relevant_docs)
        
        # Hafıza Güncelleme
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response_text})
        self._manage_conversation_memory()
        
        return response_text + sources_html