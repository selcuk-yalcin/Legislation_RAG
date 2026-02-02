"""
Query expansion and intelligent document filtering using LLM
"""

from config import MODEL_NAME, EXPANSION_TEMPERATURE, EXPANSION_MAX_TOKENS
import json


def analyze_query_context(client, query):
    """
    Analyzes the user's query to determine which document types are relevant.
    This prevents cross-contamination between sectors (Gemi, Maden, İnşaat, etc.)
    
    Args:
        client: OpenAI client instance
        query (str): The user's question
        
    Returns:
        dict: Filtering criteria with relevant document types/sectors
    """
    analysis_prompt = f"""Sen uzman bir iş güvenliği ve mevzuat analistisin. Kullanıcının sorusunu analiz edip hangi sektör/belge türünün alakalı olduğunu belirle.

SORU: "{query}"

Aşağıdaki kategorilerden hangisi soruyla ALAKALIDİR? (JSON formatında cevapla)

{{
    "sectors": ["genel", "maden", "gemi", "insaat", "tarim"],  // Alakalı sektörler (birden fazla olabilir)
    "document_types": ["KANUN", "YÖNETMELIK", "TEBLİĞ"],  // Alakalı belge türleri
    "exclude_keywords": [],  // Kesinlikle HARİÇ tutulacak kelimeler (örn: ["gemi", "deniz"] eğer soru gemicilikle alakalı DEĞİLSE)
    "is_general": true,  // Genel bir iş güvenliği sorusu mu? (true ise sektör filtresi UYGULANMAZ)
    "confidence": 0.9  // Ne kadar eminsin? (0.0-1.0)
}}

ÖNEMLİ KURALLAR:
1. Eğer soru GENEL iş güvenliği ile ilgiliyse (işveren yükümlülükleri, risk değerlendirmesi, vb.) → "is_general": true
2. Eğer soru SPESİFİK bir sektörden bahsediyorsa (gemi, maden, inşaat) → "is_general": false ve sadece o sektörü ekle
3. "exclude_keywords"'e sadece kesinlikle alakasız olan sektörleri ekle (örn: soru "işyeri hekimi" ise "gemi", "deniz" exclude edilebilir)
4. Şüphen varsa "is_general": true yap, fazla filtreleme yapmaktan kaçın

Sadece JSON çıktısı ver, açıklama yapma."""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,  # Daha deterministik sonuçlar için düşük temperature
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response (sometimes LLM adds markdown)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        analysis = json.loads(result_text)
        
        print(f"🔍 Query Analysis:")
        print(f"   • Is General: {analysis.get('is_general', True)}")
        print(f"   • Sectors: {analysis.get('sectors', ['genel'])}")
        print(f"   • Exclude: {analysis.get('exclude_keywords', [])}")
        print(f"   • Confidence: {analysis.get('confidence', 0.5)}")
        
        return analysis
        
    except Exception as e:
        print(f"⚠️ Query analysis failed: {e}, using general context")
        return {
            "sectors": ["genel"],
            "document_types": ["KANUN", "YÖNETMELIK", "TEBLİĞ"],
            "exclude_keywords": [],
            "is_general": True,
            "confidence": 0.0
        }


def build_metadata_filter(analysis):
    """
    Builds MongoDB metadata filter based on query analysis.
    
    Args:
        analysis (dict): Query analysis result from analyze_query_context()
        
    Returns:
        dict: MongoDB filter dictionary or None if no filtering needed
    """
    # If it's a general question, don't apply sector filters
    if analysis.get('is_general', True):
        print("📂 No sector filtering (general query)")
        return None
    
    filters = {}
    
    # Sector filtering
    sectors = analysis.get('sectors', [])
    if sectors and 'genel' not in sectors:
        # Create OR condition for document titles containing sector keywords
        sector_filters = []
        for sector in sectors:
            sector_keywords = {
                'maden': ['maden', 'madencilik'],
                'gemi': ['gemi', 'deniz', 'denizcilik', 'maritime'],
                'insaat': ['inşaat', 'yapı', 'bina'],
                'tarim': ['tarım', 'zirai', 'çiftçi']
            }
            
            keywords = sector_keywords.get(sector.lower(), [sector])
            for keyword in keywords:
                sector_filters.append({
                    'metadata.document_title': {'$regex': keyword, '$options': 'i'}
                })
        
        if sector_filters:
            filters['$or'] = sector_filters
    
    # Exclude keywords (NOT filter)
    exclude = analysis.get('exclude_keywords', [])
    if exclude:
        for keyword in exclude:
            # Exclude documents containing these keywords in title
            if 'metadata.document_title' not in filters:
                filters['metadata.document_title'] = {}
            filters['metadata.document_title']['$not'] = {'$regex': keyword, '$options': 'i'}
    
    print(f"📂 Applied metadata filter: {filters if filters else 'None'}")
    return filters if filters else None


def expand_query(client, original_query):
    """
    Expands the user's query with legal terminology and synonyms using the LLM.
    
    Args:
        client: OpenAI client instance
        original_query (str): The original user query
        
    Returns:
        str: Expanded query with additional legal terms
    """
    expansion_prompt = f"""Sen uzman bir hukuk asistanısın. Görevin, kullanıcının sorusunu arama motorunda daha iyi sonuç verecek şekilde hukuki terimler ve eş anlamlılarla genişletmektir.
    
Kurallar:
1. Soruyu cevaplama, sadece anahtar kelimeler ekle.
2. Türkçe karakterlere dikkat et.
3. Eğer soru 'yaptırım', 'ceza' içeriyorsa: "idari para cezası", "hapis cezası", "yaptırımlar", "madde 26" terimlerini ekle.

Soru: "{original_query}"
Genişletilmiş:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": expansion_prompt}],
            temperature=EXPANSION_TEMPERATURE,
            max_tokens=EXPANSION_MAX_TOKENS
        )
        expanded = response.choices[0].message.content
        print(f"🔍 Expanded Query: {expanded}")
        return expanded
    except Exception as e:
        print(f"⚠️ Expansion failed, using original query. Error: {e}")
        return original_query
