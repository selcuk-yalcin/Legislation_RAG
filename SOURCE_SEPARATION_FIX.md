# 🔧 KAYNAK AYRIŞTIRMA ÇÖZÜMÜ

## Problem
- Sistem `documents` (mevzuat) ve `guides` (rehberler) kaynaklarını birleştiriyor
- LLM, farklı kaynaklardan gelen bilgileri sentezleyerek tek yanıt üretiyor
- Mevzuatta geçen ifadeler **aynen** değil, **yorumlanmış** halde sunuluyor

## Çözüm 1: Kaynak Tipine Göre Ayrı Yanıt (ÖNERİLEN) ⭐

### Değişiklikler

#### A) `rag_pipeline.py` - Context'i kaynak tipine göre ayır

```python
# Step 5: Bağlam Oluşturma - KAYNAK TİPİNE GÖRE AYRI
documents_docs = [d for d in relevant_docs if d.metadata.get('collection_type') != 'guide']
guides_docs = [d for d in relevant_docs if d.metadata.get('collection_type') == 'guide']

# Mevzuat kaynakları
mevzuat_context = ""
if documents_docs:
    mevzuat_context = "\n\n🏛️ MEVZUAT KAYNAKLARI (Kanun/Yönetmelik):\n" + "="*70 + "\n\n"
    mevzuat_context += "\n\n".join([
        f"KAYNAK [{clean_source_name(doc)}]: {doc.page_content}" 
        for doc in documents_docs
    ])

# Rehber kaynakları
guide_context = ""
if guides_docs:
    guide_context = "\n\n📚 REHBER KAYNAKLARI (Kılavuz/Uygulama Rehberi):\n" + "="*70 + "\n\n"
    guide_context += "\n\n".join([
        f"REHBER [{clean_source_name(doc)}]: {doc.page_content}" 
        for doc in guides_docs
    ])

# Birleşik context
context = mevzuat_context + guide_context
```

#### B) Prompt'u güncelleyin - Kaynak tipleri arasında ayrım yap

```python
rag_prompt = f"""
Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış bir danışmansın.

ÖNEMLİ AYIRIM:
1. **Mevzuat Kaynakları** (🏛️): Kanun ve yönetmeliklerde GEÇTİĞİ GİBİ aktarılmalı
   - Kesin ifadeler kullan: "...dır", "...malıdır", "...olacaktır"
   - Direkt alıntı yap
   - Kaynak: [Yönetmelik/Kanun Tam Adı]

2. **Rehber Kaynakları** (📚): Uygulama önerileri ve açıklamalar
   - Öneri niteliğinde ifadeler kullan: "...olmalıdır", "önerilir", "faydalı olabilir"
   - Kaynak: [Rehber Adı]

YANIT FORMATI:
Her bilgi için kaynağın tipini belirt:

**🏛️ Mevzuat:** (Kanun/yönetmelikte aynen geçen hüküm)
- İçerik [Kaynak]

**📚 Uygulama Önerisi:** (Rehberlerden/kılavuzlardan)
- İçerik [Kaynak]

ÖRNEK YANIT:

**🏛️ Mevzuat:**
İşveren, işyerinde iş sağlığı ve güvenliği hizmetlerini yürütmekle yükümlüdür [6331 Sayılı İş Sağlığı ve Güvenliği Kanunu].

**📚 Uygulama Önerisi:**
KOBİ'lerde çalışanların düzenli eğitim alması ve bilgilendirilmesi önerilir. Bu eğitimler iş kazalarının önlenmesi açısından kritik öneme sahiptir [Tekstil Sektörü İsg Rehberi].

KURALLAR:
1. Mevzuat kaynaklarını AYNEN alıntıla (kelime değiştirme)
2. Rehber kaynaklarını öneri niteliğinde sun
3. Her bilgi için kaynak tipini açıkça belirt (🏛️ veya 📚)
4. "Fıkra", "Bent", "Madde" kelimelerini kullanma

Mevzuat ve Rehber İçeriği:
----------------------------------
{context}
----------------------------------

Kullanıcı Sorusu: {user_input}

Yanıt (Kaynak Tipine Göre Ayrıştırılmış Format):"""
```

#### C) Kaynakları gösterirken de ayır

```python
def _format_sources(self, documents):
    """Format sources with clear separation between legislation and guides"""
    if not documents:
        return ""
    
    # Kaynak tipine göre ayır
    mevzuat_docs = [d for d in documents if d.metadata.get('collection_type') != 'guide']
    guide_docs = [d for d in documents if d.metadata.get('collection_type') == 'guide']
    
    sources = "\n\n" + "═" * 70 + "\n"
    sources += "📚 CEVABINIZ İÇİN KULLANILAN KAYNAKLAR\n"
    sources += "═" * 70 + "\n\n"
    
    # Mevzuat kaynakları
    if mevzuat_docs:
        sources += "🏛️ **MEVZUAT KAYNAKLARI (Yasal Dayanak)**\n"
        sources += "─" * 70 + "\n"
        for idx, doc in enumerate(mevzuat_docs, 1):
            title = doc.metadata.get('document_title', doc.metadata.get('source_file', 'Bilinmeyen'))
            content = doc.page_content.replace('\n', ' ').strip()[:300]
            sources += f"{idx}. {title}\n"
            sources += f"   💬 Alıntı: \"{content}...\"\n\n"
    
    # Rehber kaynakları
    if guide_docs:
        sources += "\n📚 **REHBER KAYNAKLARI (Uygulama Önerileri)**\n"
        sources += "─" * 70 + "\n"
        for idx, doc in enumerate(guide_docs, 1):
            title = doc.metadata.get('guide_title', doc.metadata.get('source_file', 'Bilinmeyen'))
            content = doc.page_content.replace('\n', ' ').strip()[:300]
            sources += f"{idx}. {title}\n"
            sources += f"   💬 Öneri: \"{content}...\"\n\n"
    
    sources += "═" * 70 + "\n"
    return sources
```

## Çözüm 2: Sadece Mevzuat Ara (Basit)

Eğer sadece mevzuatta geçen bilgileri istiyorsanız:

```python
# mongodb_vector_store.py - similarity_search çağrısında:
results = vectorstore.similarity_search(
    query,
    k=100,
    search_web=True,
    search_guides=False  # ❌ Rehberleri devre dışı bırak
)
```

## Çözüm 3: Kullanıcıya Seçim Hakkı Ver

```python
# hybrid_pipeline.py içinde:
def query(self, user_input, source_preference="all"):
    """
    Args:
        source_preference: "all", "legislation_only", "guides_only"
    """
    if source_preference == "legislation_only":
        # Sadece documents'tan ara
        search_web = False
        search_guides = False
    elif source_preference == "guides_only":
        # Sadece guides'tan ara
        search_web = False
        search_guides = True
    else:
        # Hepsinden ara ama ayrı göster
        search_web = True
        search_guides = True
```

## Önerilen Uygulama Planı

1. ✅ **Çözüm 1**'i uygula (kaynak tiplerine göre ayrı yanıt)
2. ✅ Prompt'u güncelle (mevzuat vs rehber ayrımı)
3. ✅ `_format_sources` metodunu güncelle
4. ✅ Test et

## Beklenen Sonuç

```
**🏛️ Mevzuat:**
İşveren, işyerinde mevcut riskleri belirlemeli ve bu risklere yönelik önlemler 
almalıdır [6331 Sayılı İş Sağlığı ve Güvenliği Kanunu].

Risk değerlendirmesi yapılırken, işyerinde var olan ya da dışarıdan gelebilecek 
tehlikeler dikkate alınır [İş Sağlığı ve Güvenliği Risk Değerlendirmesi Yönetmeliği].

**📚 Uygulama Önerisi:**
KOBİ'lerde çalışanların iş sağlığı ve güvenliği konularında düzenli eğitim alması 
sağlanmalı ve bilgilendirilmelidir. Bu eğitimler, iş kazalarının önlenmesi açısından 
kritik öneme sahiptir [Tekstil Sektörü İsg Rehberi].
```

Bu şekilde kullanıcı:
- Hangi bilginin **yasal zorunluluk** olduğunu görür (🏛️)
- Hangi bilginin **uygulama önerisi** olduğunu görür (📚)
- Mevzuatta geçen ifadeler **aynen** aktarılır
- Rehberlerden gelen bilgiler **öneri** olarak sunulur
