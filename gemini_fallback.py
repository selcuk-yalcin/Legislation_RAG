"""
Gemini Flash Fallback for RAG System
Uses 1M context window to search entire regulations when RAG confidence is low
Now uses OpenRouter API (google/gemini-2.0-flash-exp:free) - No separate API key needed!
"""

import os
from typing import Dict, List, Optional
from openai import OpenAI


class GeminiFallback:
    """
    Gemini Flash 2.0 fallback search with 1M context window via OpenRouter
    Used when primary RAG returns low confidence results
    """
    
    def __init__(self, openrouter_client: Optional[OpenAI] = None):
        """
        Initialize Gemini Flash client via OpenRouter
        
        Args:
            openrouter_client: OpenRouter client instance (if None, creates new one)
        """
        # Use existing OpenRouter client or create new one
        if openrouter_client:
            self.client = openrouter_client
        else:
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment")
            
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key
            )

        # Use Gemini 2.5 Flash Lite (free tier on OpenRouter, 1M context!)
        self.model_name = "google/gemini-2.5-flash-lite"

        print(f"✅ Gemini 2.5 Flash Lite initialized via OpenRouter (1M context window, FREE)")

    def load_full_regulation(
        self,
        regulation_name: str,
        mongo_collection
    ) -> str:
        """
        Load entire regulation from MongoDB by reconstructing from chunks
        
        Args:
            regulation_name: Document title to search for
            mongo_collection: MongoDB collection instance
            
        Returns:
            Full regulation text with proper MADDE structure
        """
        # Find all chunks for this regulation
        # CRITICAL: Sort by page number and chunk index, NOT madde_number (string sorting bug)
        chunks = list(mongo_collection.find({
            "metadata.document_title": {
                "$regex": regulation_name,
                "$options": "i"
            }
        }).sort([("metadata.page", 1), ("metadata.chunk_index", 1)]))
        
        if not chunks:
            return f"# {regulation_name}\n\n(Yönetmelik metni bulunamadı)"
        
        # Reconstruct document
        full_text = f"# {regulation_name}\n\n"
        current_madde = None
        madde_content = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            madde_num = metadata.get('madde_number', 'Unknown')
            content = chunk.get('content', '')
            
            # Skip empty chunks
            if not content.strip():
                continue
            
            # New MADDE section
            if madde_num != current_madde and madde_num != 'Unknown':
                # Write previous MADDE if exists
                if current_madde and madde_content:
                    full_text += f"\n## MADDE {current_madde}\n\n"
                    full_text += "\n\n".join(madde_content) + "\n"
                    madde_content = []
                
                current_madde = madde_num
            
            # Add content
            madde_content.append(content)
        
        # Write last MADDE
        if current_madde and madde_content:
            full_text += f"\n## MADDE {current_madde}\n\n"
            full_text += "\n\n".join(madde_content) + "\n"
        
        return full_text
    
    def fallback_search(
        self,
        query: str,
        regulation_name: str,
        mongo_collection,
        include_metadata: bool = True
    ) -> Dict:
        """
        Send entire regulation + query to Gemini Flash
        
        Args:
            query: User question
            regulation_name: Which regulation to search
            mongo_collection: MongoDB collection
            include_metadata: Include chunk metadata in response
            
        Returns:
            {
                "answer": str,
                "method": "gemini_fallback",
                "regulation": str,
                "full_doc_length": int,
                "confidence": float,
                "model": str
            }
        """
        print(f"\n🔍 Loading full regulation: {regulation_name}...")
        
        # Load complete document
        full_doc = self.load_full_regulation(regulation_name, mongo_collection)
        doc_length = len(full_doc)
        
        print(f"   • Document length: {doc_length:,} characters")
        print(f"   • Context window: 1M tokens (~4M chars)")
        
        # Construct prompt with legal hallucination barriers
        prompt = f"""Sen bir Türk hukuk uzmanısın. Aşağıdaki yönetmeliğin TAMAMINI okuyarak kullanıcının sorusunu yanıtlayacaksın.

# YÖNETMELİK METNİ:
{full_doc}

# KULLANICI SORUSU:
{query}

# TALİMATLAR:
1. Yönetmeliğin tamamını dikkatlice incele
2. Soruyla ilgili TÜM MADDE'leri bul
3. Her MADDE için tam atıf yap (örnek: "MADDE 14, Fıkra 2")
4. Birden fazla MADDE ilgiliyse hepsini belirt
5. Eğer konuyla ilgili hiçbir MADDE yoksa açıkça "Bu konuda yönetmelikte açık hüküm bulunmamaktadır" de
6. Cevabını Türkçe hukuk diliyle ver
7. Kesinlikle yönetmelik dışı bilgi ekleme

# HUKUKİ HALÜSİNASYON BARİYERİ:
⚠️  UYARI 1: Eğer madde metninde açıkça geçmiyorsa, "Yorumuma göre böyledir" gibi ifadeler kullanma. Sadece metindeki lafza sadık kal.
⚠️  UYARI 2: Cevapta kullandığın her bilginin yanına, o bilgiyi aldığın madde numarasını köşeli parantez içinde yaz [MADDE X].
⚠️  UYARI 3: Metinde olmayan bir bilgiyi asla ekleme. Emin değilsen, "Bu konuda açık hüküm yoktur" de.

# CEVAP:
"""

        try:
            # OpenRouter API call with Gemini 2.0 Flash
            print("   • Sending to Gemini 2.0 Flash via OpenRouter...")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": """Sen bir Türk hukuk uzmanısın. Verilen yönetmelik metninden sorulara yanıt veriyorsun.

HUKUKİ HALÜSİNASYON BARİYERİ:
⚠️ UYARI 1: Sadece metindeki lafza sadık kal. "Yorumuma göre" gibi ifadeler kullanma.
⚠️ UYARI 2: Her bilgi için [MADDE X] formatında kaynak göster.
⚠️ UYARI 3: Metinde olmayan bilgi ekleme. Emin değilsen "Bu konuda açık hüküm yoktur" de."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2048
            )
            
            answer = response.choices[0].message.content.strip()
            
            print(f"   ✅ Response received ({len(answer)} chars)")
            
            # Extract MADDE references from answer for sources
            import re
            madde_pattern = r'\[MADDE\s+(\d+)\]'
            madde_matches = re.findall(madde_pattern, answer, re.IGNORECASE)
            
            # Create sources list from MADDE references
            sources = []
            for madde_num in set(madde_matches):  # Remove duplicates
                sources.append({
                    "document_title": regulation_name,
                    "madde_number": madde_num,
                    "method": "gemini_fallback",
                    "citation": f"[MADDE {madde_num}]"
                })
            
            # Format sources for display
            sources_html = "\n\n" + "═" * 70 + "\n"
            sources_html += "📚 CEVABINIZ İÇİN KULLANILAN KAYNAKLAR\n"
            sources_html += "═" * 70 + "\n\n"
            
            if sources:
                for idx, src in enumerate(sources, 1):
                    sources_html += f"📄 Kaynak {idx}: {src['document_title']}\n"
                    sources_html += "─" * 70 + "\n"
                    sources_html += f"📌 MADDE: {src['madde_number']}\n"
                    sources_html += f"🔍 Yöntem: Gemini Fallback (Full Document Search)\n"
                    sources_html += f"💬 Atıf: {src['citation']}\n\n"
            else:
                sources_html += "⚠️  No specific MADDE citations found in answer.\n\n"
            
            sources_html += "═" * 70 + "\n"
            sources_html += "💡 Not: Gemini 1M context window ile tüm düzenleme tarandı.\n"
            
            return {
                "answer": answer + sources_html,
                "method": "gemini_fallback_openrouter",
                "regulation": regulation_name,
                "full_doc_length": doc_length,
                "confidence": 0.90,  # High confidence (saw full doc)
                "model": self.model_name,
                "api": "openrouter",
                "sources": sources  # For API response
            }
            
        except Exception as e:
            print(f"   ❌ OpenRouter/Gemini API error: {e}")
            
            return {
                "answer": f"Gemini Fallback hatası: {str(e)}",
                "method": "gemini_fallback_error",
                "regulation": regulation_name,
                "full_doc_length": doc_length,
                "confidence": 0.0,
                "model": self.model_name,
                "error": str(e)
            }
    
    def multi_regulation_search(
        self,
        query: str,
        regulation_names: List[str],
        mongo_collection
    ) -> Dict:
        """
        Search across multiple regulations (when regulation type is unclear)
        
        Args:
            query: User question
            regulation_names: List of regulation names to search
            mongo_collection: MongoDB collection
            
        Returns:
            Best answer from all regulations
        """
        print(f"\n🔍 Multi-regulation search across {len(regulation_names)} documents...")
        
        results = []
        
        for reg_name in regulation_names:
            result = self.fallback_search(query, reg_name, mongo_collection)
            
            # Skip errors
            if "error" not in result:
                results.append(result)
        
        # Return best result (most detailed answer)
        if results:
            best = max(results, key=lambda x: len(x['answer']))
            best['method'] = 'gemini_multi_regulation'
            best['regulations_searched'] = len(regulation_names)
            return best
        
        return {
            "answer": "Hiçbir yönetmelikte ilgili bilgi bulunamadı.",
            "method": "gemini_multi_regulation_failed",
            "regulations_searched": len(regulation_names),
            "confidence": 0.0
        }


if __name__ == "__main__":
    # Test Gemini Fallback
    import sys
    
    if not GEMINI_AVAILABLE:
        print("❌ google-generativeai not installed")
        print("Install: pip install google-generativeai")
        sys.exit(1)
    
    # Check for API key
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ GEMINI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("export GEMINI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Test with MongoDB
    from pymongo import MongoClient
    
    MONGO_URI = "mongodb+srv://infera:Hoffnung_1986@mevzuatdb.qqpyi1b.mongodb.net/?appName=mevzuatdb"
    
    print("=" * 80)
    print("🧪 GEMINI FALLBACK TEST")
    print("=" * 80)
    
    try:
        # Initialize
        print("\n1️⃣  Initializing Gemini Flash...")
        fallback = GeminiFallback()
        
        # Connect to MongoDB
        print("\n2️⃣  Connecting to MongoDB...")
        client = MongoClient(MONGO_URI)
        db = client["mevzuat_db"]
        collection = db["documents"]
        
        total_docs = collection.count_documents({})
        print(f"   • {total_docs:,} documents in database")
        
        # Test query
        test_query = "Patlayıcı ortamda işverenin yükümlülükleri nelerdir?"
        regulation = "PATLAYICI ORTAM"
        
        print(f"\n3️⃣  Testing fallback search...")
        print(f"   • Query: {test_query}")
        print(f"   • Regulation: {regulation}")
        
        result = fallback.fallback_search(
            test_query,
            regulation,
            collection
        )
        
        print("\n" + "=" * 80)
        print("📊 RESULT")
        print("=" * 80)
        print(f"\nMethod: {result['method']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Document Length: {result.get('full_doc_length', 0):,} chars")
        print(f"\nAnswer Preview:")
        print(result['answer'][:500])
        print("..." if len(result['answer']) > 500 else "")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
