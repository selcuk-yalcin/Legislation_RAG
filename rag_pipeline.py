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
    MEMORY_STRATEGY,
    RERANK_SCORE_THRESHOLD
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
    
    def _agentic_document_filter(self, user_query, documents, query_analysis):
        """
        ADIM 4: AGENTIC FİLTRELEME (Self-Correction)
        GPT-4o-mini'ye döküman başlıklarını gösterip gereksizleri elemesini söyler.
        Maliyet: Çok ucuz (~0.5 saniye ekler)
        
        Args:
            user_query: Kullanıcının sorusu
            documents: Rerank edilmiş dökümanlar
            query_analysis: Niyet analizi sonucu
            
        Returns:
            Filtrelenmiş döküman listesi
        """
        if not documents:
            return documents
        
        # Döküman başlıklarını çıkar
        doc_titles = []
        for i, doc in enumerate(documents):
            title = doc.metadata.get('document_title') or doc.metadata.get('source_file', 'Bilinmeyen')
            title = title.replace('.pdf', '').replace('.PDF', '')
            doc_titles.append(f"{i+1}. {title}")
        
        primary_sector = query_analysis.get('primary_sector', 'Genel')
        
        filter_prompt = f"""Sen uzman bir mevzuat analistisin. Kullanıcının sorusuna cevap verebilecek ALAKALI dökümanları seç.

KULLANICI SORUSU: "{user_query}"
SEKTÖR: {primary_sector}

DÖKÜMAN BAŞLIKLARI:
{chr(10).join(doc_titles)}

GÖREV: Yukarıdaki dökümanlardan hangilerini KULLANMAMALI? (Alakasız olanları listele)

**KURALLAR:**
1. Eğer soru "{primary_sector}" sektörüyle ilgiliyse, SADECE o sektör dökümanlarını koru
2. Alakasız veya yanlış sektör dökümanlarını listele (örn: soru "işçi sağlığı" ise "Gemi" dökümanı alakasız)
3. Eğer TÜM dökümanlar alakalıysa → "HEPSİ ALAKALI" yaz
4. Eğer BAZI dökümanlar alakasızsa → Sadece numaralarını yaz: "2, 5, 7" (virgülle ayır)

Cevap (sadece numaralar veya "HEPSİ ALAKALI"):"""

        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": filter_prompt}],
                temperature=0.0,
                max_tokens=50
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            if "HEPSİ ALAKALI" in result or "HEPSI" in result:
                print(f"✅ ADIM 4 - AGENTIC: Tüm {len(documents)} döküman alakalı")
                return documents
            
            # Alakasız döküman numaralarını parse et
            excluded_indices = set()
            import re
            numbers = re.findall(r'\d+', result)
            for num in numbers:
                idx = int(num) - 1  # 1-based'den 0-based'e çevir
                if 0 <= idx < len(documents):
                    excluded_indices.add(idx)
            
            # Alakalı dökümanları filtrele
            filtered_docs = [doc for i, doc in enumerate(documents) if i not in excluded_indices]
            
            print(f"✅ ADIM 4 - AGENTIC: {len(filtered_docs)}/{len(documents)} döküman alakalı (elenen: {len(excluded_indices)})")
            
            return filtered_docs if filtered_docs else documents  # En az 1 döküman olsun
            
        except Exception as e:
            print(f"⚠️ ADIM 4 - AGENTIC filtre hatası: {e}, tüm dökümanlar kullanılıyor")
            return documents
    
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
        """
        PERPLEXITY TARZI - Artık cevap içinde kaynak listesi yok
        Sadece inline citation'lar kullanılacak [1][2][3]
        """
        # Artık kaynak formatlaması frontend'de pop-up olarak gösterilecek
        # Bu metod şimdilik boş string döndürür
        return ""
    
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
        
        # Step 4: Voyage Reranker ile Nokta Atışı + Skor Eşiği
        if self.reranker and initial_docs:
            print(f"🎯 Voyage Reranker {len(initial_docs)} dökümanı sıralıyor...")
            relevant_docs = self.reranker.rerank_documents(
                user_input, 
                initial_docs, 
                top_k=TOP_RERANKED_K,
                score_threshold=RERANK_SCORE_THRESHOLD  # ADIM 3: Skor eşiği
            )
        else:
            relevant_docs = initial_docs[:TOP_RERANKED_K]
        
        # Step 4.5: Agentic Document Filtering (Self-Correction)
        relevant_docs = self._agentic_document_filter(user_input, relevant_docs, query_analysis)
        
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

4. DETAYLI VE AÇIKLAYICI YAZ.
   - Gereksiz giriş cümlesi yazma ("Elbette, bu konuda...", "Bu sorunun cevabı...")
   - Direkt cevaba gir
   - Aynı bilgiyi tekrar etme
   - AMA yeterli detay ver, birden fazla ilgili madde varsa hepsini yaz
   - Gerekirse birden fazla kaynaktan bilgi birleştir

5. KAYNAK GÖSTER - ÖNEMLİ!
   - Her alıntının HEMEN ARKASINA o alıntının kaynağını yaz: [Kaynak Adı]
   - SADECE o cümlede/paragrafta kullandığın kaynağı göster
   - Aynı kaynağı tekrar kullanırsan tekrar yaz
   - .pdf uzantısı YAZMA
   - Dosya adı yerine düzgün Türkçe başlık kullan
   - Kaynak adını bağlamda KAYNAK [...] veya REHBER [...] başlığından al

Örnek:
"İşveren; yapılan risk değerlendirmesi sonuçlarına göre, kontrol tedbirlerini düzenli olarak izler ve risk değerlendirmesini yeniler." [İş Sağlığı ve Güvenliği Risk Değerlendirmesi Yönetmeliği]

"Kadın çalışanlar, gebe oldukları anlaşılan kadınlar ve doğum tarihinden itibaren bir yıl geçmemiş kadınlar gece çalışamaz." [Kadın Çalışanların Gece Postalarında Çalıştırılma Koşulları Hakkında Yönetmelik]

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
3. Her alıntının sonunda [Kaynak Adı] formatında kaynak belirt. Örnek: "..." [İşyerlerinde Acil Durumlar Hakkında Yönetmelik]
4. Metinde yoksa: "Sağlanan kaynaklarda bu konuya ilişkin doğrudan bir hüküm bulunamadı." de. Uydurma. Yönlendirme yapma. Liste verme.
5. Detaylı ve açıklayıcı cevap ver. Birden fazla ilgili kaynak varsa hepsini kullan. Gereksiz tekrar yapma ama yeterli bilgi ver.
6. Mevzuat = kesin hüküm, tırnak alıntı. Rehber = öneri niteliğinde.
7. Kaynak adını köşeli parantez içinde yaz: [Tam Türkçe Ad]. .pdf YAZMA. Dosya adı YAZMA. MADDE numarası YAZMA.
8. EMOJİ KULLANMA. Yönlendirme mesajı YAZMA."""
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
        
        # Kaynak bilgilerini hazırla - Tam metin ile
        sources_list = []
        for idx, doc in enumerate(relevant_docs, 1):
            # Rehber ise guide_title, değilse document_title kullan
            if doc.metadata.get('collection_type') == 'guide':
                raw_title = doc.metadata.get('guide_title') or doc.metadata.get('source_file', 'Bilinmeyen Rehber')
            else:
                raw_title = doc.metadata.get('document_title') or doc.metadata.get('source_file', 'Bilinmeyen Belge')
            
            clean_title = self._clean_title(raw_title)
            
            source_info = {
                "id": idx,
                "title": clean_title,
                "name": clean_title,
                "file": clean_title,
                "madde_number": doc.metadata.get('madde_number', ''),
                "source_type": doc.metadata.get('collection_type', 'document'),
                "source_url": doc.metadata.get('source_url', ''),
                "full_text": doc.page_content,  # TAM METİN
                "excerpt": self._extract_clean_preview(doc.page_content, max_length=250),
                "score": getattr(doc, 'score', 0)
            }
            sources_list.append(source_info)
        
        # Citation numaralarını kaldırdık - cevap olduğu gibi
        return {
            "answer": response_text,
            "method": "internal",
            "sources": sources_list,
            "source_count": len(relevant_docs)
        }