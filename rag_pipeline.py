"""
Main RAG pipeline with intelligent memory management
"""

from config import (
    MODEL_NAME,
    TEMPERATURE,
    MAX_TOKENS,
    INITIAL_RETRIEVAL_K,
    MAX_CONVERSATION_HISTORY,
    MEMORY_STRATEGY
)
from query_expansion import expand_query


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
        
        # Group documents by source file
        sources_by_file = {}
        for doc in documents:
            source_file = doc.metadata.get('source_file', 'Bilinmeyen Kaynak')
            if source_file not in sources_by_file:
                sources_by_file[source_file] = []
            sources_by_file[source_file].append(doc)
        
        # Format each source group
        source_num = 1
        for source_file, docs in sources_by_file.items():
            # Clean up source file name
            clean_name = source_file.replace('.pdf', '').replace('_', ' ')
            
            sources += f"📄 Kaynak {source_num}: {clean_name}\n"
            sources += "─" * 70 + "\n"
            
            # Show pages from this document
            pages = []
            for doc in docs:
                page_label = doc.metadata.get('page_label', doc.metadata.get('page', 'N/A'))
                if page_label not in pages:
                    pages.append(page_label)
            
            if pages:
                sources += f"📖 Sayfa(lar): {', '.join(map(str, pages))}\n"
            
            # Show source directory (KANUN/TEBLİĞ) from first doc
            if docs:
                source_dir = docs[0].metadata.get('source_dir', '')
                if source_dir:
                    category = "📜 Kanun/Yönetmelik" if "KANUN" in source_dir else "📋 Tebliğ"
                    sources += f"{category}\n"
            
            # Show content preview from first document
            if docs:
                content_preview = docs[0].page_content[:200].replace('\n', ' ').strip()
                sources += f"💬 Alıntı: \"{content_preview}...\"\n"
            
            sources += "\n"
            source_num += 1
        
        sources += "═" * 70 + "\n"
        sources += "💡 Not: Kaynak dökümanlar MongoDB Atlas'tan otomatik seçilmiştir.\n"
        
        return sources
    
    def generate_response(self, user_input):
        """
        Main RAG Pipeline:
        1. Expand Query -> 2. Retrieve (Broad) -> 3. Rerank -> 4. Generate Answer
        
        Args:
            user_input (str): User's question
            
        Returns:
            str: Answer with source citations
        """
        # Step 1: Expand the query
        search_query = expand_query(self.client, user_input)
        
        # Step 2: Retrieve broad set of documents
        initial_docs = self.vectorstore.similarity_search(
            search_query,
            k=INITIAL_RETRIEVAL_K
        )
        
        # Step 3: Rerank documents
        relevant_docs = self.reranker.rerank_documents(search_query, initial_docs)
        
        # Step 4: Build context
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Manage conversation memory (keep only recent messages)
        self._manage_conversation_memory()
        
        # Step 5: Construct prompt
        rag_prompt = f"""Based on the following excerpts from Law 6331, answer the question.

CRITICAL INSTRUCTIONS:
1. ONLY use the information provided below.
2. If the question is NOT related to Law 6331, respond: "Bu soru 6331 sayılı İş Sağlığı ve Güvenliği Kanunu ile ilgili değildir."
3. If the answer is not in the context, respond: "Bu bilgi kanun metninde yer almamaktadır."
4. Always cite the specific article number (Madde X). Do NOT cite page numbers.
5. Provide detailed and accurate answers.

Law 6331 Content:
{context}

Question: {user_input}

Answer (must include article number):"""
        
        messages = [
            {
                "role": "system",
                "content": "You are a legal expert specialized ONLY in Turkish Law 6331."
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
