"""
Main RAG pipeline with intelligent memory management
"""

from config import (
    MODEL_NAME,
    TEMPERATURE,
    MAX_TOKENS,
    INITIAL_RETRIEVAL_K,
    TOP_RERANKED_K,
    MAX_CONVERSATION_HISTORY,
    MEMORY_STRATEGY
)
from query_expansion import expand_query, analyze_query_context, build_metadata_filter


class RAGPipeline:
    """Main RAG Pipeline for Law 6331 Q&A with Smart Memory"""
    
    def __init__(self, client, vectorstore, reranker, max_history=None):
        """
        Initialize RAG Pipeline.
        
        Args:
            client: OpenAI client instance
            vectorstore: Vector store instance (MongoDB/Chroma)
            reranker: RerankerService instance
            max_history: Maximum conversation history to keep (default from config)
        """
        self.client = client
        self.vectorstore = vectorstore
        self.reranker = reranker
        self.conversation_history = []
        self.max_history = max_history or MAX_CONVERSATION_HISTORY
        self.memory_strategy = MEMORY_STRATEGY
    
    def _manage_conversation_memory(self):
        """
        Intelligent conversation memory management.
        Keeps only recent messages to prevent context overflow.
        """
        if len(self.conversation_history) > self.max_history:
            if self.memory_strategy == "sliding_window":
                # Keep only the last N messages
                self.conversation_history = self.conversation_history[-self.max_history:]
            elif self.memory_strategy == "summarize":
                # TODO: Implement conversation summarization
                # For now, use sliding window
                self.conversation_history = self.conversation_history[-self.max_history:]
    
    def _format_sources(self, documents):
        """
        Format source documents in a beautiful, user-friendly way.
        NOW WITH MADDE-LEVEL PRECISION!
        
        Args:
            documents: List of Document objects with metadata
            
        Returns:
            str: Formatted sources string
        """
        if not documents:
            return ""
        
        sources = "\n\n" + "═" * 70 + "\n"
        sources += "📚 CEVABINIZ İÇİN KULLANILAN KAYNAKLAR\n"
        sources += "═" * 70 + "\n\n"
        
        # Format each source with MADDE information
        for idx, doc in enumerate(documents, 1):
            # Get enhanced metadata
            document_title = doc.metadata.get('document_title', 'Bilinmeyen Belge')
            madde_number = doc.metadata.get('madde_number', 'Bilinmeyen')
            full_reference = doc.metadata.get('full_reference', document_title)
            document_type = doc.metadata.get('document_type', '')
            page = doc.metadata.get('page', 'N/A')
            
            sources += f"📄 Kaynak {idx}: {full_reference}\n"
            sources += "─" * 70 + "\n"
            
            # Show document type
            if document_type:
                category = "📜 Kanun/Yönetmelik" if "KANUN" in document_type else "📋 Tebliğ"
                sources += f"{category}\n"
            
            # Show MADDE number if available
            if madde_number != "Bilinmeyen":
                sources += f"📌 MADDE: {madde_number}\n"
            
            # Show page number
            sources += f"📖 Sayfa: {page}\n"
            
            # Show structural information if available
            if doc.metadata.get('has_bent', False):
                bent_count = doc.metadata.get('bent_count', 0)
                sources += f"📋 Bu maddede {bent_count} bent bulunmaktadır\n"
            
            if doc.metadata.get('has_fikra', False):
                fikra_count = doc.metadata.get('fikra_count', 0)
                sources += f"📝 Bu maddede {fikra_count} fıkra bulunmaktadır\n"
            
            # Show content preview
            content_preview = doc.page_content[:200].replace('\n', ' ').strip()
            sources += f"💬 Alıntı: \"{content_preview}...\"\n"
            
            sources += "\n"
        
        sources += "═" * 70 + "\n"
        sources += "💡 Not: Kaynaklar MADDE bazlı parçalama ile hassas şekilde seçilmiştir.\n"
        
        return sources
    
    def generate_response(self, user_input):
        """
        Main RAG Pipeline:
        1. Analyze Query Context (NEW!) -> 2. Build Metadata Filter (NEW!) 
        3. Expand Query -> 4. Retrieve (Broad, with filtering) -> 5. Rerank -> 6. Generate Answer
        
        Args:
            user_input (str): User's question
            
        Returns:
            str: Answer with source citations
        """
        # Step 1: Analyze query to determine relevant sectors/documents (INTELLIGENT FILTERING!)
        print("\n🧠 Analyzing query context for intelligent filtering...")
        query_analysis = analyze_query_context(self.client, user_input)
        
        # Step 2: Build metadata filter based on analysis
        metadata_filter = build_metadata_filter(query_analysis)
        
        # Step 3: Expand the query (temporarily disabled to avoid model issues)
        # search_query = expand_query(self.client, user_input)
        search_query = user_input  # Use original query directly
        
        # Step 4: Retrieve broad set of documents WITH METADATA FILTERING
        print(f"\n📚 Retrieving documents from MongoDB...")
        initial_docs = self.vectorstore.similarity_search(
            search_query,
            k=INITIAL_RETRIEVAL_K,
            filter_dict=metadata_filter  # 🔥 SMART FILTERING APPLIED HERE!
        )
        
        if not initial_docs:
            print("⚠️ No documents found with current filter, retrying without filter...")
            # Fallback: retry without filter if no results
            initial_docs = self.vectorstore.similarity_search(
                search_query,
                k=INITIAL_RETRIEVAL_K,
                filter_dict=None
            )
        
        # Step 5: Rerank documents with Voyage AI
        print(f"\n🎯 Reranking {len(initial_docs)} documents...")
        if self.reranker:
            relevant_docs = self.reranker.rerank_documents(search_query, initial_docs, top_k=TOP_RERANKED_K)
        else:
            # Fallback: use top documents without reranking
            relevant_docs = initial_docs[:TOP_RERANKED_K]
        
        print(f"✅ Selected {len(relevant_docs)} most relevant documents")
        
        # Step 6: Build context
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Manage conversation memory (keep only recent messages)
        self._manage_conversation_memory()
        
        # Step 7: Construct prompt
        rag_prompt = f"""Aşağıdaki iş sağlığı ve güvenliği mevzuatı bilgilerine dayanarak soruyu yanıtla.

KRİTİK TALİMATLAR:
1. SADECE aşağıda verilen bilgileri kullan.
2. Cevap kaynaklarda yoksa: "Bu bilgi mevcut mevzuat kaynaklarında bulunamadı."
3. Her zaman kaynak madde numarasını belirt (Madde X veya Yönetmelik Madde Y).
4. Detaylı ve doğru cevaplar ver.
5. Türkçe cevap ver.

Mevzuat İçeriği:
{context}

Soru: {user_input}

Cevap (madde numarası ile):"""
        
        messages = [
            {
                "role": "system",
                "content": "Sen Türk İş Sağlığı ve Güvenliği mevzuatı konusunda uzman bir hukuk danışmanısın."
            }
        ] + self.conversation_history[:-1] + [
            {
                "role": "user",
                "content": rag_prompt
            }
        ]
        
        # Step 6: Generate answer
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        response_text = response.choices[0].message.content
        
        # Step 7: Format sources with beautiful presentation
        sources = self._format_sources(relevant_docs)
        
        full_response = response_text + sources
        
        # Add assistant response to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Manage memory after adding response
        self._manage_conversation_memory()
        
        return full_response
    
    def reset_conversation(self):
        """Resets the conversation history"""
        self.conversation_history = []
    
    def get_conversation_stats(self):
        """Get conversation memory statistics"""
        return {
            "total_messages": len(self.conversation_history),
            "max_allowed": self.max_history,
            "memory_strategy": self.memory_strategy,
            "memory_usage_percent": (len(self.conversation_history) / self.max_history * 100) if self.max_history > 0 else 0
        }
