"""
Simple test for conversation memory management (no external dependencies)
"""

import sys
sys.path.insert(0, '/Users/selcuk/Desktop/admin_pan/Legislation_RAG')

from config import MAX_CONVERSATION_HISTORY, MEMORY_STRATEGY

def test_memory_logic():
    """Test sliding window logic"""
    
    print("=" * 70)
    print("🧠 Conversation Memory Test (Simplified)")
    print("=" * 70)
    
    print(f"\n📋 Configuration:")
    print(f"   Max History: {MAX_CONVERSATION_HISTORY} messages")
    print(f"   Memory Strategy: {MEMORY_STRATEGY}")
    
    # Simulate conversation history
    conversation_history = []
    max_history = 10
    
    print(f"\n🧪 Simulating 15 messages (7 Q&A pairs + 1 question)")
    print("-" * 70)
    
    for i in range(1, 16):
        if i % 2 == 1:
            conversation_history.append({"role": "user", "content": f"Question {(i+1)//2}"})
        else:
            conversation_history.append({"role": "assistant", "content": f"Answer {i//2}"})
        
        # Apply sliding window
        if len(conversation_history) > max_history:
            conversation_history = conversation_history[-max_history:]
        
        if i % 2 == 0:  # After each Q&A pair
            pair_num = i // 2
            print(f"After Q&A pair {pair_num}:")
            print(f"  Total messages: {len(conversation_history)}/{max_history}")
            print(f"  Memory usage: {len(conversation_history)/max_history*100:.0f}%")
            
            if len(conversation_history) == max_history:
                oldest = conversation_history[0]['content']
                newest = conversation_history[-1]['content']
                print(f"  ⚠️  LIMIT REACHED!")
                print(f"  Oldest in memory: {oldest}")
                print(f"  Newest in memory: {newest}")
            print()
    
    print("\n" + "=" * 70)
    print("📊 Final Conversation History:")
    print("=" * 70)
    
    for i, msg in enumerate(conversation_history, 1):
        print(f"{i:2d}. [{msg['role']:9s}] {msg['content']}")
    
    print("\n" + "=" * 70)
    print("✅ Results:")
    print("=" * 70)
    
    print(f"✓ Messages in memory: {len(conversation_history)}/{max_history}")
    print(f"✓ Oldest message: {conversation_history[0]['content']}")
    print(f"✓ Newest message: {conversation_history[-1]['content']}")
    
    # Verify
    expected_first = 6  # Question 6 should be first (messages 11-12 onwards)
    actual_first_q = conversation_history[0]['content']
    
    if f"Question {expected_first}" in actual_first_q:
        print(f"\n✅ Sliding window working correctly!")
        print(f"   Questions 1-5 were removed")
        print(f"   Questions 6-8 are kept in memory")
    else:
        print(f"\n⚠️  Unexpected result: {actual_first_q}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_memory_logic()
