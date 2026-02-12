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
    
    def _clean_title(self, raw_title):
        """Basliklari temizle ve duzenle"""
        import re
        
        if not raw_title or raw_title in ['Bilinmeyen Belge', 'Bilinmeyen Rehber', 'Bilinmeyen']:
            return "Belge Adi Bulunamadi"
        
        # .pdf uzantisini kaldir
        title = raw_title.replace('.pdf', '').replace('.PDF', '')
        
        # Basinda [PDF] varsa kaldir
        title = title.replace('[PDF]', '').replace('[pdf]', '').strip()
        
        # Alt cizgileri ve tire isaretlerini bosluga cevir
        title = title.replace('_', ' ').replace('-', ' ')
        
        # Coklu bosluklari temizle
        title = re.sub(r'\s+', ' ', title).strip()
        
        # TAMAMEN BUYUK HARF ise Title Case yap
        if title == title.upper() and len(title) > 5:
            title = title.title()
        
        # Cok kisa ve anlamsiz basliklari filtrele
        if len(title) < 10 and not any(keyword in title.lower() for keyword in ['kanun', 'yonetmelik', 'teblig', 'genelge']):
            return "Isimsiz Belge"
        
        return title
    
    def _extract_clean_preview(self, text, max_length=300):
        """
        Metinden anlamlı bir önizleme çıkar - tam cümleler kullanarak
        """
        import re
        
        # Yeni satırları ve fazla boşlukları temizle
        clean_text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
        
        if len(clean_text) <= max_length:
            return clean_text
        
        # max_length'e kadar al
        preview = clean_text[:max_length]
        
        # Son tam cümleyi bul (. ! ? ile biten)
        last_sentence_end = max(
            preview.rfind('. '),
            preview.rfind('! '),
            preview.rfind('? ')
        )
        
        # Eğer tam cümle bulunduysa, oradan kes
        if last_sentence_end > max_length * 0.5:  # En az yarısı dolu olmalı
            preview = preview[:last_sentence_end + 1]
        else:
            # Yoksa en son kelimeye kadar al
            last_space = preview.rfind(' ')
            if last_space > 0:
                preview = preview[:last_space] + '...'
            else:
                preview = preview + '...'
        
        return preview.strip()
    
    def _format_sources(self, documents):
        """Format sources with clear separation between legislation and guides"""
        if not documents:
            return ""
        
        # Kaynak tipine gore ayir
        mevzuat_docs = [d for d in documents if d.metadata.get('collection_type') != 'guide']
        guide_docs = [d for d in documents if d.metadata.get('collection_type') == 'guide']
        
        sources = "\n\n" + "=" * 70 + "\n"
        sources += "KAYNAKLAR\n"
        sources += "=" * 70 + "\n\n"
        
        # Mevzuat kaynaklari
        if mevzuat_docs:
            sources += "MEVZUAT KAYNAKLARI:\n"
            sources += "-" * 70 + "\n"
            for idx, doc in enumerate(mevzuat_docs, 1):
                # Basligi temizle
                raw_title = doc.metadata.get('document_title', doc.metadata.get('source_file', 'Bilinmeyen Belge'))
                clean_title = self._clean_title(raw_title)
                
                # Link varsa ekle
                source_url = doc.metadata.get('source_url', '')
                if source_url and source_url.startswith('http'):
                    sources += f"{idx}. {clean_title}\n"
                    sources += f"   Link: {source_url}\n"
                else:
                    sources += f"{idx}. {clean_title}\n"
                
                # Icerik onizleme - TAM CUMLELER AL
                content_preview = self._extract_clean_preview(doc.page_content, max_length=300)
                sources += f"   İlgili Bölüm: \"{content_preview}\"\n\n"
        
        # Rehber kaynaklari
        if guide_docs:
            sources += "REHBER KAYNAKLARI:\n"
            sources += "-" * 70 + "\n"
            for idx, doc in enumerate(guide_docs, 1):
                # Basligi temizle
                raw_title = doc.metadata.get('guide_title', doc.metadata.get('source_file', 'Bilinmeyen Rehber'))
                clean_title = self._clean_title(raw_title)
                
                # Link varsa ekle
                source_url = doc.metadata.get('source_url', '')
                if source_url and source_url.startswith('http'):
                    sources += f"{idx}. {clean_title}\n"
                    sources += f"   Link: {source_url}\n"
                else:
                    sources += f"{idx}. {clean_title}\n"
                
                # Icerik onizleme - TAM CUMLELER AL
                content_preview = self._extract_clean_preview(doc.page_content, max_length=300)
                sources += f"   İlgili Bölüm: \"{content_preview}\"\n\n"
        
        sources += "=" * 70 + "\n"
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
        
        # Step 5: Bağlam Oluşturma - KAYNAK TİPİNE GÖRE AYRI
        def clean_source_name(doc):
            """source_file'dan .pdf kaldır ve düzgün başlık formatına çevir"""
            # Rehber ise guide_title kullan
            if doc.metadata.get('collection_type') == 'guide':
                raw = doc.metadata.get('guide_title') or doc.metadata.get('source_file', 'Bilinmeyen Rehber')
            else:
                raw = doc.metadata.get('document_title') or doc.metadata.get('source_file', 'Bilinmeyen Belge')
            
            # .pdf uzantısını kaldır
            name = raw.replace('.pdf', '').replace('.PDF', '')
            # Alt çizgileri boşluğa çevir
            name = name.replace('_', ' ')
            # BÜYÜK HARF ise düzgün başlık formatına çevir
            if name == name.upper():
                name = name.title()
            return name.strip()
        
        # Kaynak tipine göre ayır
        documents_docs = [d for d in relevant_docs if d.metadata.get('collection_type') != 'guide']
        guides_docs = [d for d in relevant_docs if d.metadata.get('collection_type') == 'guide']
        
        # Mevzuat kaynakları
        mevzuat_context = ""
        if documents_docs:
            mevzuat_context = "\nMEVZUAT KAYNAKLARI (Kanun/Yönetmelik - AYNEN ALINTILA):\n" + "="*70 + "\n\n"
            mevzuat_context += "\n\n".join([
                f"KAYNAK [{clean_source_name(doc)}]: {doc.page_content}" 
                for doc in documents_docs
            ])
        
        # Rehber kaynakları
        guide_context = ""
        if guides_docs:
            guide_context = "\n\nREHBER KAYNAKLARI (Kılavuz/Uygulama Rehberi - ÖNERİ NİTELİĞİNDE):\n" + "="*70 + "\n\n"
            guide_context += "\n\n".join([
                f"REHBER [{clean_source_name(doc)}]: {doc.page_content}" 
                for doc in guides_docs
            ])
        
        # Birleşik context
        context = mevzuat_context + guide_context
        
        # Step 6: Sertleştirilmiş Prompt (Hallucination Engelleyici)
        # OLD VERSION - Keeping for reference
        # rag_prompt = f"""
        # Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış, son derece titiz bir hukuk danışmanısın. 
        # Görevin, aşağıdaki 'Mevzuat İçeriği' kısmını bir hakim hassasiyetiyle incelemek ve soruyu yanıtlamaktır.
        # ...
        # """
        
        # DENETÇİ MODU - Sıkı Alıntı + Yorum Yapmama Promptu
        rag_prompt = f"""Sen bir İSG mevzuat uzmanısın. Görevin SADECE aşağıdaki metinleri kullanarak soruyu yanıtlamak.

KURALLAR:

1. METİNDEN DIŞARI ÇIKMA.
   Sana verilen mevzuat/rehber metninde ne yazıyorsa ONU yaz. Kendi cümleni EKLEME, yorum YAPMA, çıkarım YAPMA.

2. ALINTIYLA CEVAP VER.
   İlgili hükmü mevzuattaki haliyle tırnak içinde ("...") aynen aktar. Kelime değiştirme, eş anlamlı kullanma.
   Eğer metinde bir madde numarası, ek numarası veya başlık varsa (Madde 4, Ek-II, vb.) cevaba ONUNLA BAŞLA.

3. BİLGİ YOKSA "BULUNAMADI" DE.
   Dokümanda net bir rakam, süre veya bilgi yoksa şunu yaz:
   "Sağlanan kaynaklarda bu konuya ilişkin doğrudan bir hüküm bulunamadı."
   Asla "genellikle", "muhtemelen", "yaklaşık" gibi belirsiz ifadeler kullanma.
   HİÇBİR ZAMAN yönlendirme yapma, başka kaynaklar önerme veya emoji kullanma.

4. KISA VE ÖZ YAZ.
   - Gereksiz giriş cümlesi yazma ("Elbette, bu konuda...", "Bu sorunun cevabı...")
   - Direkt cevaba gir
   - Aynı bilgiyi tekrar etme
   - Hedef: en fazla 500 karakter (zorunlu değilse uzatma)

5. KAYNAK GÖSTER.
   Her alıntının sonuna [Kaynak Adı] ekle.
   - .pdf uzantısı YAZMA
   - Dosya adı yerine düzgün Türkçe başlık kullan
   - Kaynak adını bağlamda KAYNAK [...] veya REHBER [...] başlığından al

6. KAYNAK AYIRIMI.
   Mevzuat (kanun/yönetmelik) = kesin hüküm, tırnak içinde alıntı
   Rehber (kılavuz/uygulama) = öneri niteliğinde, "...önerilmektedir" formatında

YASAK DAVRANIŞLAR:
- "Bu konuda şunu söyleyebiliriz ki..." gibi dolgu cümleleri
- Metinde olmayan süre/rakam uydurma
- Aynı bilgiyi farklı kelimelerle tekrarlama
- Emoji kullanma
- Yönlendirme mesajları ("Daha spesifik soru sorun", "Bu kaynaklara bakabilirsiniz")
- Liste halinde kaynak gösterme (cevap yok ise bile)
- .pdf uzantılı dosya adları

DOĞRU CEVAP ÖRNEĞİ:
Soru: "Risk değerlendirmesi ne sıklıkla yenilenir?"

Cevap:
"İşveren; yapılan risk değerlendirmesi sonuçlarına göre, kontrol tedbirlerini düzenli olarak izler ve risk değerlendirmesini yeniler." [İş Sağlığı ve Güvenliği Risk Değerlendirmesi Yönetmeliği]

METİNLER:
{context}

Soru: {user_input}

Cevap:"""
        
        # Mesaj Geçmişi Yönetimi
        messages = [
            {
                "role": "system",
                "content": """Sen İSG mevzuat uzmanısın. Sadece verilen metne bağlı kal.

KURALLAR:
1. Metinde ne yazıyorsa ONU yaz. Yorum YAPMA, çıkarım YAPMA, dolgu cümlesi EKLEME.
2. İlgili hükmü tırnak içinde ("...") AYNEN alıntıla. Kelime değiştirme.
3. Metinde yoksa: "Sağlanan kaynaklarda bu konuya ilişkin doğrudan bir hüküm bulunamadı." de. Uydurma. Yönlendirme yapma. Liste verme.
4. Kısa ve öz yaz. Gereksiz tekrar yapma. Direkt cevaba gir.
5. Mevzuat = kesin hüküm, tırnak alıntı. Rehber = öneri niteliğinde.
6. Kaynak: [Tam Türkçe Ad] formatında. .pdf YAZMA. Dosya adı YAZMA.
7. EMOJİ KULLANMA. Yönlendirme mesajı YAZMA."""
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