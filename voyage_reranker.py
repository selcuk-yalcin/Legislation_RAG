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
    
    def rerank_documents(self, query: str, documents: List, top_k: int = 5) -> List:
        """
        Rerank documents using Voyage AI rerank-2.5-lite model
        
        Args:
            query: Search query
            documents: List of Document objects with page_content
            top_k: Number of top documents to return
            
        Returns:
            List of top-k reranked documents
        """
        try:
            if not documents:
                return []
            
            # Extract text content from documents
            doc_texts = [doc.page_content for doc in documents]
            
            print(f"⚖️ Reranking {len(documents)} documents with Voyage AI...")
            print(f"   • Model: {self.model}")
            print(f"   • Query: {query[:50]}...")
            
            # Call Voyage AI rerank API
            result = self.client.rerank(
                query=query,
                documents=doc_texts,
                model=self.model,
                top_k=min(top_k, len(documents))
            )
            
            # Build ranked documents list
            ranked_docs = []
            for item in result.results:
                ranked_docs.append(documents[item.index])
            
            print(f"✅ Reranking complete! Top {len(ranked_docs)} documents selected")
            
            return ranked_docs
            
        except Exception as e:
            print(f"❌ Voyage reranking failed!")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
            print(f"   Model attempted: {self.model}")
            print(f"   Falling back to original order (top {top_k})")
            
            # Re-raise the exception so we can see it in logs
            raise e
