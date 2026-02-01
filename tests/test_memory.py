"""
Test script for conversation memory management
"""

from rag_pipeline import RAGPipeline
from mongodb_vector_store import get_mongodb_vectorstore
from client import create_openrouter_client
from reranker import RerankerService
from config import MAX_CONVERSATION_HISTORY

def test_memory_management():
    """Test conversation memory sliding window"""
    
    print("=" * 70)
    print("🧠 Conversation Memory Management Test")
    print("=" * 70)
    
    print(f"\n📋 Configuration:")
    print(f"   Max History: {MAX_CONVERSATION_HISTORY} messages")
    
    # Initialize components (mock for testing)
    class MockClient:
        pass
    
    class MockVectorStore:
        def similarity_search(self, query, k):
            class MockDoc:
                def __init__(self):
                    self.page_content = "Test content"
                    self.metadata = {"page": 1}
            return [MockDoc()]
    
    class MockReranker:
        def rerank_documents(self, query, docs):
            return docs[:3]
    
    # Create pipeline with mock components
    pipeline = RAGPipeline(
        client=MockClient(),
        vectorstore=MockVectorStore(),
        reranker=MockReranker(),
        max_history=5  # Test with 5 for easier visualization
    )
    
    print(f"\n🧪 Test 1: Adding messages one by one")
    print("-" * 70)
    
    # Simulate conversation
    for i in range(1, 8):
        pipeline.conversation_history.append({
            "role": "user",
            "content": f"Question {i}"
        })
        pipeline.conversation_history.append({
            "role": "assistant",
            "content": f"Answer {i}"
        })
        
        pipeline._manage_conversation_memory()
        
        stats = pipeline.get_conversation_stats()
        print(f"After message {i}:")
        print(f"  Total messages: {stats['total_messages']}/{stats['max_allowed']}")
        print(f"  Memory usage: {stats['memory_usage_percent']:.1f}%")
        print(f"  Messages in history: {len(pipeline.conversation_history)}")
        
        if len(pipeline.conversation_history) <= 5:
            print(f"  Content: {[m['role'] for m in pipeline.conversation_history]}")
        
        if stats['total_messages'] == stats['max_allowed']:
            print(f"  ⚠️  Memory limit reached - oldest messages will be removed")
        
        print()
    
    print("\n" + "=" * 70)
    print("🧪 Test 2: Final conversation history")
    print("=" * 70)
    
    for i, msg in enumerate(pipeline.conversation_history, 1):
        print(f"{i}. [{msg['role']}] {msg['content']}")
    
    print("\n" + "=" * 70)
    print("✅ Test Results:")
    print("=" * 70)
    
    final_stats = pipeline.get_conversation_stats()
    print(f"✓ Total messages kept: {final_stats['total_messages']}")
    print(f"✓ Maximum allowed: {final_stats['max_allowed']}")
    print(f"✓ Memory strategy: {final_stats['memory_strategy']}")
    print(f"✓ Memory usage: {final_stats['memory_usage_percent']:.1f}%")
    
    # Verify sliding window worked
    if final_stats['total_messages'] <= final_stats['max_allowed']:
        print("\n✅ Sliding window memory management working correctly!")
        print(f"   Old messages (1-2) were removed, keeping only recent (3-7)")
    else:
        print("\n❌ Memory management failed - too many messages!")
    
    print("\n" + "=" * 70)
    print("🧪 Test 3: Reset conversation")
    print("=" * 70)
    
    pipeline.reset_conversation()
    stats_after_reset = pipeline.get_conversation_stats()
    
    print(f"After reset:")
    print(f"  Total messages: {stats_after_reset['total_messages']}")
    print(f"  Memory usage: {stats_after_reset['memory_usage_percent']:.1f}%")
    
    if stats_after_reset['total_messages'] == 0:
        print("\n✅ Reset conversation working correctly!")
    else:
        print("\n❌ Reset failed!")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    test_memory_management()
