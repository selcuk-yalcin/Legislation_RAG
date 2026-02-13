"""
Voyage AI Reranker - Railway-compatible, lightweight reranking service
Uses Voyage AI's rerank-2.5-lite model for high-quality document reranking
"""

import os
import voyageai
from typing import List
from config import VOYAGE_RERANK_MODEL


class VoyageReranker:
    """Lightweight reranker using Voyage AI API"""
    
    def __init__(self):
        """Initialize Voyage AI client"""
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY environment variable not set!")
        
        self.client = voyageai.Client(api_key=api_key)
        self.model = VOYAGE_RERANK_MODEL  # Use model from config (rerank-2.5-lite)
        
        print(f"✅ Voyage AI Reranker initialized (model: {self.model})")
    
    def rerank_documents(self, query: str, documents: List, top_k: int = 5, score_threshold: float = 0.0) -> List:
        """
        ADIM 3: RERANKER SKOR EŞİĞİ (Threshold)
        Voyage AI ile dökümanları rerank eder ve belirli skor altındakileri eler.
        
        Args:
            query: Search query
            documents: List of Document objects with page_content
            top_k: Number of top documents to return
            score_threshold: Minimum relevance score (0.0-1.0). Default 0.0 (no filtering)
                           Önerilen: 0.4-0.5 arası (alakasız dökümanları eler)
            
        Returns:
            List of top-k reranked documents above threshold
        """
        try:
            if not documents:
                return []
            
            # Extract text content from documents
            doc_texts = [doc.page_content for doc in documents]
            
            print(f"⚖️ ADIM 3 - RERANKER: {len(documents)} döküman skorlanıyor...")
            print(f"   • Model: {self.model}")
            print(f"   • Query: {query[:50]}...")
            print(f"   • Skor Eşiği: {score_threshold}")
            
            # Call Voyage AI rerank API
            result = self.client.rerank(
                query=query,
                documents=doc_texts,
                model=self.model,
                top_k=min(top_k, len(documents))
            )
            
            # Build ranked documents list with score filtering
            ranked_docs = []
            filtered_count = 0
            
            for item in result.results:
                # THRESHOLD CHECK: Sadece yüksek skorlu dökümanları al
                if item.relevance_score >= score_threshold:
                    doc = documents[item.index]
                    # Skoru metadata'ya ekle (debug için)
                    if hasattr(doc, 'metadata'):
                        doc.metadata['rerank_score'] = item.relevance_score
                    ranked_docs.append(doc)
                else:
                    filtered_count += 1
            
            print(f"✅ Reranking tamamlandı!")
            print(f"   • Kabul edilen: {len(ranked_docs)} döküman (skor >= {score_threshold})")
            print(f"   • Elenen: {filtered_count} döküman (düşük skor)")
            
            return ranked_docs
            
        except Exception as e:
            print(f"❌ Voyage reranking failed!")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
            print(f"   Model attempted: {self.model}")
            print(f"   Falling back to original order (top {top_k})")
            
            # Re-raise the exception so we can see it in logs
            raise e
