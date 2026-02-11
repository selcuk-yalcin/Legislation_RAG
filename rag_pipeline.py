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
            
            sources += f"📄 Kaynak {idx}: {document_title}\n"
            sources += "─" * 70 + "\n"
            
            # İçerik önizleme - tam içeriği gönder (limit yok)
            content_preview = doc.page_content.replace('\n', ' ').strip()
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
        
        # Step 5: Bağlam Oluşturma (source_file temizleme)
        def clean_source_name(doc):
            """source_file'dan .pdf kaldır ve düzgün başlık formatına çevir"""
            raw = doc.metadata.get('document_title') or doc.metadata.get('source_file', 'Bilinmeyen Belge')
            # .pdf uzantısını kaldır
            name = raw.replace('.pdf', '').replace('.PDF', '')
            # Alt çizgileri boşluğa çevir
            name = name.replace('_', ' ')
            # BÜYÜK HARF ise düzgün başlık formatına çevir
            if name == name.upper():
                name = name.title()
            return name.strip()
        
        context = "\n\n".join([f"KAYNAK [{clean_source_name(doc)}]: {doc.page_content}" for doc in relevant_docs])
        
        # Step 6: Sertleştirilmiş Prompt (Hallucination Engelleyici)
        # OLD VERSION - Keeping for reference
        # rag_prompt = f"""
        # Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış, son derece titiz bir hukuk danışmanısın. 
        # Görevin, aşağıdaki 'Mevzuat İçeriği' kısmını bir hakim hassasiyetiyle incelemek ve soruyu yanıtlamaktır.
        # ...
        # """
        
        # NEW VERSION - Simplified format without MADDE numbers (temporary fix)
        rag_prompt = f"""
Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış  bir danışmansın.

ÖNEMLİ: Yanıtlarında "Fıkra", "Bent", "Madde" gibi ifadeler kullanmak kesinlikle YASAKTIR.

YANIT FORMATI:
- Her önemli nokta için başlık kullan (bold formatında: **Başlık:**)
- Kaynak referanslarını köşeli parantez içinde SADECE yönetmelik/kanun adı olarak yaz
- Dosya adı (.pdf) kullanma, sadece resmi yönetmelik/kanun adını yaz
- Madde içeriğini açıklarken direkt bilgiyi yaz, madde numarasını belirtme
- Temiz, okunaklı ve madde işaretli liste formatında yanıt ver

ÖRNEK YANIT:
Soru: "Acil durum planı nasıl hazırlanır?"

**Acil Durumların Belirlenmesi:** İşyerinde meydana gelebilecek acil durumlar, tasarım veya kuruluş aşamasından itibaren belirlenmelidir [İşyerlerinde Acil Durumlar Hakkında Yönetmelik].

**Önleyici Tedbirler:** Belirlenen acil durumların olumsuz etkilerini önleyici tedbirler alınmalıdır [İşyerlerinde Acil Durumlar Hakkında Yönetmelik].

**Acil Durum Planının Hazırlanması:** İşveren, tespit edilen acil durumlara göre acil durum planı hazırlamalı ve gerekli her türlü tedbiri almalıdır [İşyerlerinde Acil Durumlar Hakkında Yönetmelik].

KAYNAK İSİMLENDİRME KURALLARI:
- "İŞ SAĞLIĞI VE GÜVENLİĞİ RİSK DEĞERLENDİRMESİ YÖNETMELİĞİ.pdf" yerine → [İş Sağlığı ve Güvenliği Risk Değerlendirmesi Yönetmeliği]
- "6331_SAYILI_KANUN.pdf" yerine → [6331 Sayılı İş Sağlığı ve Güvenliği Kanunu]
- Her zaman düzgün Türkçe başlık formatında yaz (ilk harf büyük, geri kalan küçük)
- .pdf uzantısı ASLA yazma

YASAK REFERANS ÖRNEKLERİ (BUNLARI ASLA YAZMA):
❌ [Fıkra 1, Bent A]
❌ [Madde 14]
❌ [Fıkra 2]
❌ [Madde 14, Fıkra 2]
❌ [6331_SAYILI_KANUN.pdf]
❌ [, Fıkra 1, Bent A]
❌ İşveren, bütün iş kazalarının kaydını tutar [Fıkra 1, Bent A]
❌ Sosyal Güvenlik Kurumuna bildirimde bulunmakla yükümlüdür [MADDE 14, Fıkra 2]

DOĞRU REFERANS ÖRNEKLERİ:
✅ [6331 Sayılı İş Sağlığı ve Güvenliği Kanunu]
✅ [İş Sağlığı ve Güvenliği Risk Değerlendirmesi Yönetmeliği]
✅ [İşyerlerinde Acil Durumlar Hakkında Yönetmelik]
✅ [Yapı İşlerinde İş Sağlığı ve Güvenliği Yönetmeliği]
✅ İşveren, bütün iş kazalarının kaydını tutmalıdır [6331 Sayılı İş Sağlığı ve Güvenliği Kanunu]
✅ Sosyal Güvenlik Kurumuna bildirimde bulunmakla yükümlüdür [6331 Sayılı İş Sağlığı ve Güvenliği Kanunu]

KURALLAR:
1. SADECE aşağıdaki mevzuat içeriğine dayan
2. Her bilginin sonuna köşeli parantez içinde TAM yönetmelik/kanun adı yaz
3. Bilgi yoksa: en yakın ilgili bilgileri sun ve hangi mevzuatın incelenmesi gerektiğini belirt
4. Spekülatif ifadeler kullanma
5. "Fıkra", "Bent", "Madde" kelimelerini hiçbir şekilde yanıtında kullanma
6. ASLA boş veya genel bir "bilgi bulunamadı" cevabı verme — her zaman context'ten çıkarılabilecek en yakın bilgiyi sun

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
                "content": """Sen İSG mevzuatı danışmanısın. KESİN KURALLAR:
1. Yanıtlarını **Başlık:** formatında ver
2. Kaynak referanslarını SADECE [Yönetmelik/Kanun Tam Adı] şeklinde ekle
3. "Fıkra", "Bent", "Madde" kelimelerini yanıtlarında ASLA kullanma
4. Dosya adı (.pdf) kullanma
5. Sadece sağlanan metinlere dayan
6. Kaynak adını bağlamda KAYNAK [...] başlığından al, içerik metnindeki fıkra/bent/madde numaralarını referans olarak gösterme
7. Madde içeriğini açıklarken direkt bilgiyi yaz, numaralandırma yapma
8. ASLA boş veya genel "bilgi bulunamadı" cevabı verme — en yakın ilgili bilgileri sun"""
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
        
        # Kaynak bilgilerini hazırla
        sources_list = []
        for doc in relevant_docs:
            source_info = {
                "title": doc.metadata.get('document_title', doc.metadata.get('source_file', 'Bilinmeyen')),
                "madde_number": doc.metadata.get('madde_number', ''),
                "source_type": doc.metadata.get('source_type', 'document'),
                "source_url": doc.metadata.get('source_url', ''),
                "score": getattr(doc, 'score', 0)
            }
            sources_list.append(source_info)
        
        return {
            "answer": response_text + sources_html,
            "method": "internal",
            "sources": sources_list,
            "source_count": len(relevant_docs)
        }