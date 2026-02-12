"""
Command-line interface for the RAG system
"""

import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')


def run_cli(rag_pipeline):
    """
    Runs command-line interface for Q&A
    
    Args:
        rag_pipeline: RAGPipeline instance
    """
    print("\n" + "="*80)
    print("🏛️ Law 6331 Q&A System - Command Line Interface")
    print("="*80)
    print("\nType 'quit' or 'exit' to end the session.")
    print("Type 'reset' to clear conversation history.\n")
    
    while True:
        try:
            question = input("\n❓ Your Question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if question.lower() == 'reset':
                rag_pipeline.reset_conversation()
                print("✅ Conversation history cleared!")
                continue
            
            if not question:
                continue
            
            print("\n💬 Answer:")
            print("-" * 80)
            answer = rag_pipeline.generate_response(question)
            print(answer)
            print("-" * 80)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
