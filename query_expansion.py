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
    analysis_prompt = f"""Sen uzman bir iş güvenliği ve mevzuat analistisin. Kullanıcının sorusunu analiz edip hangi sektör/belge türünün alakalı olduğunu KESIN olarak belirle.

SORU: "{query}"

Aşağıdaki kategorilerden hangisi soruyla ALAKALIDİR? (JSON formatında cevapla)

{{
    "primary_sector": "Genel",  // Ana sektör: "Genel", "Maden", "İnşaat", "Gemi", "Tarım" (TEK SEÇENEK)
    "sectors": ["genel"],  // Alakalı sektörler listesi (birden fazla olabilir)
    "document_types": ["KANUN", "YÖNETMELIK", "TEBLİĞ"],  // Alakalı belge türleri
    "exclude_keywords": [],  // Kesinlikle HARİÇ tutulacak kelimeler/sektörler
    "is_general": true,  // Genel bir iş güvenliği sorusu mu? (true ise sektör filtresi UYGULANMAZ)
    "confidence": 0.9  // Ne kadar eminsin? (0.0-1.0)
}}

**KRİTİK KURALLAR (SIKICA UYGULANMALI):**

1. **MADEN Tespiti**: Eğer soruda "maden", "madencilik", "yeraltı", "ocak", "kömür" gibi kelimeler GEÇİYORSA:
   → "primary_sector": "Maden"
   → "is_general": false
   → "sectors": ["maden"]
   → "exclude_keywords": ["gemi", "deniz", "inşaat"]

2. **GEMİ Tespiti**: Eğer soruda "gemi", "deniz", "denizci", "liman", "tersane" GEÇİYORSA:
   → "primary_sector": "Gemi"
   → "is_general": false
   → "sectors": ["gemi"]
   → "exclude_keywords": ["maden", "inşaat"]

3. **İNŞAAT Tespiti**: Eğer soruda "inşaat", "şantiye", "yapı", "bina" GEÇİYORSA:
   → "primary_sector": "İnşaat"
   → "is_general": false
   → "sectors": ["insaat"]
   → "exclude_keywords": ["maden", "gemi", "deniz"]

4. **GENEL (Default)**: Eğer yukarıdaki hiçbir sektör belirtilmemişse (örn: "işveren yükümlülükleri", "iş kazası", "işçi sağlığı"):
   → "primary_sector": "Genel"
   → "is_general": true
   → "sectors": ["genel"]
   → "exclude_keywords": ["maden", "gemi", "deniz", "tersane", "ocak"]

5. **ŞÜPHELİ DURUMLAR**: Eğer soruda sektör belirtilmemiş ama genel iş güvenliği konusu varsa → "Genel" seç

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
        
        print(f"🔍 ADIM 1 - NİYET ANALİZİ:")
        print(f"   ✓ Ana Sektör: {analysis.get('primary_sector', 'Genel')}")
        print(f"   ✓ Is General: {analysis.get('is_general', True)}")
        print(f"   ✓ İlgili Sektörler: {analysis.get('sectors', ['genel'])}")
        print(f"   ✓ Hariç Tutulanlar: {analysis.get('exclude_keywords', [])}")
        print(f"   ✓ Güven: {analysis.get('confidence', 0.5)}")
        
        return analysis
        
    except Exception as e:
        print(f"⚠️ Query analysis failed: {e}, using general context")
        return {
            "primary_sector": "Genel",
            "sectors": ["genel"],
            "document_types": ["KANUN", "YÖNETMELIK", "TEBLİĞ"],
            "exclude_keywords": [],
            "is_general": True,
            "confidence": 0.0
        }


def build_metadata_filter(analysis):
    """
    ADIM 2: SERT METADATA FİLTRELEME
    MongoDB'da sektör bazlı kesin filtreleme yapar.
    Yanlış dökümanın sisteme girme ihtimali %0'a iner.
    
    Args:
        analysis (dict): Query analysis result from analyze_query_context()
        
    Returns:
        dict: MongoDB filter dictionary or None if no filtering needed
    """
    primary_sector = analysis.get('primary_sector', 'Genel')
    is_general = analysis.get('is_general', True)
    exclude_keywords = analysis.get('exclude_keywords', [])
    
    # Genel sorularda sektörel filtreleme YAPMA
    if is_general or primary_sector == 'Genel':
        # Ancak hariç tutulanları filtrele (örn: "işçi sağlığı" sorusunda maden dökümanı gösterme)
        if exclude_keywords:
            exclude_filter = {
                'metadata.document_title': {
                    '$not': {'$regex': '|'.join(exclude_keywords), '$options': 'i'}
                }
            }
            print(f"📂 ADIM 2 - GENEL SORU (Sadece hariç tutma): {exclude_keywords}")
            return exclude_filter
        else:
            print("📂 ADIM 2 - GENEL SORU (Filtre yok)")
            return None
    
    # Sektöre özel SERT FİLTRE
    filters = {}
    
    # Sektör keyword mapping
    sector_keywords = {
        'Maden': ['maden', 'madencilik', 'ocak', 'yeraltı', 'kömür', 'taş', 'cevher'],
        'Gemi': ['gemi', 'deniz', 'denizci', 'liman', 'tersane', 'maritime', 'ship'],
        'İnşaat': ['inşaat', 'yapı', 'bina', 'şantiye', 'construction'],
        'Tarım': ['tarım', 'zirai', 'çiftçi', 'agricultural']
    }
    
    # İlgili sektör keyword'leri
    target_keywords = sector_keywords.get(primary_sector, [primary_sector.lower()])
    
    # INCLUDE filtresi: Bu sektör keyword'lerini IÇEREN dökümanları getir
    sector_filter = {
        'metadata.document_title': {
            '$regex': '|'.join(target_keywords), 
            '$options': 'i'
        }
    }
    
    # EXCLUDE filtresi: Hariç tutulan keyword'leri IÇERMEYEN dökümanları getir
    if exclude_keywords:
        # Hem include hem exclude varsa AND koşulu kur
        filters = {
            '$and': [
                sector_filter,
                {
                    'metadata.document_title': {
                        '$not': {'$regex': '|'.join(exclude_keywords), '$options': 'i'}
                    }
                }
            ]
        }
        print(f"📂 ADIM 2 - SERT FİLTRE: Sektör={primary_sector} (SADECE {target_keywords}, HARİÇ {exclude_keywords})")
    else:
        filters = sector_filter
        print(f"📂 ADIM 2 - SERT FİLTRE: Sektör={primary_sector} (SADECE {target_keywords})")
    
    return filters


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
