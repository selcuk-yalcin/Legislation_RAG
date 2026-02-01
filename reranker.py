"""
Reranking functionality using FlashRank
"""

from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from config import RERANKER_MODEL, FLASHRANK_CACHE_DIR, INITIAL_RETRIEVAL_K, TOP_RERANKED_K


class RerankerService:
    """Service for reranking retrieved documents"""
    
    def __init__(self):
        """Initialize the reranker model"""
        print("\n⚖️ Loading Reranker Model...")
        import os
        # ChromaDB telemetri kapatma
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY"] = "False"
        os.environ["POSTHOG_DISABLED"] = "1"
        
        self.ranker = Ranker(
            model_name=RERANKER_MODEL,
            cache_dir=FLASHRANK_CACHE_DIR
        )
        print("✅ Reranker ready!")
    
    def rerank_documents(self, query, documents, top_k=TOP_RERANKED_K):
        """
        Reranks documents based on relevance to the query.
        
        Args:
            query (str): The search query
            documents (list): List of retrieved documents
            top_k (int): Number of top documents to return
            
        Returns:
            list: Reranked list of Document objects
        """
        print("⚖️ Reranking documents...")
        
        # Prepare passages for reranking
        passages = [
            {
                "id": str(i),
                "text": doc.page_content,
                "meta": doc.metadata
            }
            for i, doc in enumerate(documents)
        ]
        
        # Rerank
        rerank_request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerank_request)
        top_results = results[:top_k]
        
        # Convert back to Document objects
        relevant_docs = [
            Document(page_content=res['text'], metadata=res['meta'])
            for res in top_results
        ]
        
        return relevant_docs
