"""
Query expansion using LLM
"""

from config import MODEL_NAME, EXPANSION_TEMPERATURE, EXPANSION_MAX_TOKENS


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
