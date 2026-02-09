"""
Web server using Flask for Railway deployment

MongoDB Vector Store Version - Optimized for Railway Deployment

API Endpoints:
    POST /api/ask - Submit a question
    POST /api/reset - Reset conversation history
    GET /health - Health check endpoint
    GET /stats - Database statistics
"""

import os
import sys
import warnings

from flask import Flask, request, jsonify
from flask_cors import CORS

# Suppress warnings
warnings.filterwarnings('ignore')

# Import modules
from client import create_openrouter_client
from mongodb_vector_store import get_mongodb_vectorstore, mongodb_store_exists
from voyage_reranker import VoyageReranker  # Voyage AI reranker
from rag_pipeline import RAGPipeline
from hybrid_pipeline import HybridRAGOrchestrator  # Hybrid orchestrator

# Import Arize Phoenix tracing
try:
    from arize_tracing import initialize_tracing, trace_rag_query, get_tracing_status
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    print("⚠️  arize_tracing module not available, tracing disabled")

# Initialize Flask app
app = Flask(__name__)

# Enable CORS with proper configuration
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Global variables for RAG components
rag_pipeline = None
hybrid_orchestrator = None
openrouter_client = None  # Shared OpenRouter client


def initialize_rag_system():
    """Initialize the RAG system components"""
    global rag_pipeline, hybrid_orchestrator, openrouter_client
    
    if rag_pipeline is not None:
        return  # Already initialized
    
    print("🚀 Initializing Legislation RAG System (MongoDB + Hybrid)...\n")
    
    # 1. MongoDB'de veri var mı kontrol et
    if not mongodb_store_exists():
        print("❌ MongoDB'de döküman bulunamadı!")
        raise Exception("MongoDB'de döküman yok. Lütfen preprocessing.py scriptini çalıştırın.")
    
    # 2. Create OpenRouter client (shared for RAG + Gemini)
    openrouter_client = create_openrouter_client()
    
    # 3. MongoDB Vector Store'u yükle (ChromaDB yerine)
    vectorstore = get_mongodb_vectorstore()
    stats = vectorstore.get_collection_stats()
    print(f"✅ MongoDB bağlantısı başarılı: {stats['total_documents']} döküman yüklü\n")
    
    # 4. Initialize Voyage AI reranker
    reranker = VoyageReranker()
    
    # 5. Create RAG pipeline
    rag_pipeline = RAGPipeline(openrouter_client, vectorstore, reranker)
    
    # 6. Create Hybrid Orchestrator (with Gemini 2.0 Flash fallback via OpenRouter)
    try:
        hybrid_orchestrator = HybridRAGOrchestrator(
            rag_pipeline=rag_pipeline,
            mongo_collection=vectorstore.collection,
            openrouter_client=openrouter_client,
            enable_fallback=True
        )
        print("✅ Hybrid orchestrator with Gemini 2.0 Flash ready!")
    except Exception as e:
        print(f"⚠️  Hybrid orchestrator disabled: {e}")
        hybrid_orchestrator = None
    
    print("\n✅ Legislation RAG system ready!\n")
    
    # Initialize Arize Phoenix tracing
    if TRACING_AVAILABLE:
        try:
            initialize_tracing()
        except Exception as e:
            print(f"⚠️  Arize tracing init error: {e}")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # MongoDB bağlantısını kontrol et
        from mongodb_vector_store import MongoDBVectorStore
        store = MongoDBVectorStore()
        health = store.health_check()
        
        return jsonify({
            'status': 'healthy',
            'message': 'Legislation RAG System (MongoDB)',
            'mongodb': health,
            'tracing': get_tracing_status() if TRACING_AVAILABLE else {'enabled': False}
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/debug/env', methods=['GET'])
def debug_env():
    """Debug endpoint to check environment variables"""
    import os
    from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME, VOYAGE_API_KEY
    
    return jsonify({
        'mongo_uri': MONGO_URI[:50] + '...' if MONGO_URI else 'NOT SET',
        'mongo_db': MONGO_DB_NAME,
        'mongo_collection': MONGO_COLLECTION_NAME,
        'voyage_api_key': 'SET' if VOYAGE_API_KEY else 'NOT SET',
        'env_check': {
            'MONGO_URI_env': os.environ.get('MONGO_URI', 'NOT IN ENV')[:50] + '...',
            'MONGO_DB_NAME_env': os.environ.get('MONGO_DB_NAME', 'NOT IN ENV')
        }
    }), 200


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    try:
        initialize_rag_system()
        
        if rag_pipeline is None:
            return jsonify({
                'error': 'RAG system not initialized',
                'status': 'error'
            }), 500
        
        # MongoDB'den istatistikleri al
        stats = rag_pipeline.vectorstore.get_collection_stats()
        
        return jsonify({
            'total_documents': stats['total_documents'],
            'total_chunks': stats['total_documents'],  # Backward compatibility
            'database': stats['database'],
            'collection': stats['collection'],
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'total_documents': 0
        }), 500


@app.route('/query', methods=['POST', 'OPTIONS'])
def query_question():
    """
    Answer a question using the RAG system (alternative endpoint)
    
    Request Body:
        {
            "question": "Your question here",
            "conversation_history": [] (optional)
        }
    
    Response:
        {
            "answer": "The generated answer with sources",
            "sources": [],
            "status": "success"
        }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Get question from request
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                'error': 'Missing question in request body',
                'status': 'error'
            }), 400
        
        question = data['question'].strip()
        
        if not question:
            return jsonify({
                'error': 'Question cannot be empty',
                'status': 'error'
            }), 400
        
        # Initialize RAG system if not already done
        initialize_rag_system()
        
        # Track query start time for tracing
        import time as _time
        _query_start = _time.time()
        
        # Use Hybrid Orchestrator if available, otherwise fallback to RAG
        if hybrid_orchestrator:
            # Intelligent routing: RAG → Score → Gemini fallback if needed
            result = hybrid_orchestrator.query(question)
            
            _query_latency = (_time.time() - _query_start) * 1000  # ms
            
            # Extract sources from result
            sources = []
            if 'sources' in result and result['sources']:
                for src in result['sources']:
                    if isinstance(src, dict):
                        sources.append({
                            'file': src.get('metadata', {}).get('file', 'Bilinmeyen Kaynak'),
                            'page': src.get('metadata', {}).get('page', '?'),
                            'content': src.get('content', '')[:200] + '...' if src.get('content') else ''
                        })
            
            # Trace to Arize Phoenix
            if TRACING_AVAILABLE:
                try:
                    trace_rag_query(
                        question=question,
                        method=result.get('method', 'unknown'),
                        confidence=result.get('confidence', 0),
                        answer=result.get('answer', ''),
                        sources=sources,
                        sources_count=len(sources),
                        latency=_query_latency,
                        metadata={
                            'normalized_query': result.get('normalized_query'),
                            'fallback_reason': result.get('fallback_reason', '')
                        }
                    )
                except Exception as trace_err:
                    print(f"⚠️  Tracing error: {trace_err}")
            
            return jsonify({
                'answer': result['answer'],
                'method': result.get('method', 'unknown'),
                'confidence': result.get('confidence', 0),
                'regulation': result.get('regulation', ''),
                'fallback_reason': result.get('fallback_reason', ''),
                'sources': sources,
                'normalized_query': result.get('normalized_query', {}),
                'status': 'success'
            }), 200
        else:
            # Fallback to basic RAG
            answer = rag_pipeline.generate_response(question)
            
            _query_latency = (_time.time() - _query_start) * 1000
            
            # Trace basic RAG
            if TRACING_AVAILABLE:
                try:
                    trace_rag_query(
                        question=question,
                        method='basic_rag',
                        answer=answer,
                        sources=[],
                        latency=_query_latency,
                        confidence=0.5,
                        metadata={'fallback': 'basic_rag'}
                    )
                except Exception:
                    pass
            
            return jsonify({
                'answer': answer,
                'method': 'basic_rag',
                'sources': [],
                'status': 'success'
            }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'answer': 'Üzgünüm, bir hata oluştu.'
        }), 500


@app.route('/reset', methods=['POST', 'OPTIONS'])
def reset_query():
    """
    Reset conversation history (alternative endpoint)
    
    Response:
        {
            "message": "Conversation history cleared",
            "status": "success"
        }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        if rag_pipeline is None:
            return jsonify({
                'error': 'RAG system not initialized',
                'status': 'error'
            }), 400
        
        rag_pipeline.reset_conversation()
        
        return jsonify({
            'message': 'Conversation history cleared',
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/feedback', methods=['POST', 'OPTIONS'])
def submit_feedback():
    """
    Store user feedback (thumbs up/down) for a bot response.
    Also logs feedback as a span in Arize Phoenix tracing.
    
    Request Body:
        {
            "message_id": "12345",
            "question": "User's question",
            "answer": "Bot's answer",
            "feedback": "up" or "down",
            "timestamp": "2026-02-09T..."
        }
    
    Response:
        {
            "status": "success",
            "message": "Feedback recorded"
        }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data or 'feedback' not in data:
            return jsonify({
                'error': 'Missing feedback in request body',
                'status': 'error'
            }), 400
        
        feedback_type = data['feedback']  # "up" or "down"
        message_id = data.get('message_id', '')
        question = data.get('question', '')
        answer = data.get('answer', '')
        timestamp = data.get('timestamp', '')
        
        # Log feedback
        print(f"\n{'👍' if feedback_type == 'up' else '👎'} FEEDBACK RECEIVED")
        print(f"   Message ID: {message_id}")
        print(f"   Question: {question[:100]}...")
        print(f"   Feedback: {feedback_type}")
        print(f"   Timestamp: {timestamp}")
        
        # Store in MongoDB feedback collection
        try:
            from mongodb_vector_store import MongoDBVectorStore
            store = MongoDBVectorStore()
            feedback_collection = store.db['user_feedback']
            feedback_collection.insert_one({
                'message_id': message_id,
                'question': question,
                'answer': answer[:500],  # Truncate for storage
                'feedback': feedback_type,
                'timestamp': timestamp,
                'created_at': __import__('datetime').datetime.utcnow()
            })
            print(f"   ✅ Feedback saved to MongoDB")
        except Exception as mongo_err:
            print(f"   ⚠️  MongoDB save failed: {mongo_err}")
        
        # Log to Arize Phoenix tracing if available
        try:
            from arize_tracing import log_feedback_span
            log_feedback_span(message_id, question, answer, feedback_type)
        except Exception as trace_err:
            print(f"   ⚠️  Tracing feedback log skipped: {trace_err}")
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback recorded'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """
    Answer a question using the RAG system
    
    Request Body:
        {
            "question": "Your question here"
        }
    
    Response:
        {
            "answer": "The generated answer with sources",
            "status": "success"
        }
    """
    try:
        # Get question from request
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                'error': 'Missing question in request body',
                'status': 'error'
            }), 400
        
        question = data['question'].strip()
        
        if not question:
            return jsonify({
                'error': 'Question cannot be empty',
                'status': 'error'
            }), 400
        
        # Initialize RAG system if not already done
        initialize_rag_system()
        
        # Generate answer
        answer = rag_pipeline.generate_response(question)
        
        return jsonify({
            'answer': answer,
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset_conversation():
    """
    Reset conversation history
    
    Response:
        {
            "message": "Conversation history cleared",
            "status": "success"
        }
    """
    try:
        if rag_pipeline is None:
            return jsonify({
                'error': 'RAG system not initialized',
                'status': 'error'
            }), 400
        
        rag_pipeline.reset_conversation()
        
        return jsonify({
            'message': 'Conversation history cleared',
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/memory', methods=['GET'])
def get_memory_stats():
    """
    Get conversation memory statistics
    
    Response:
        {
            "total_messages": 6,
            "max_allowed": 10,
            "memory_strategy": "sliding_window",
            "memory_usage_percent": 60.0,
            "status": "success"
        }
    """
    try:
        if rag_pipeline is None:
            return jsonify({
                'error': 'RAG system not initialized',
                'status': 'error'
            }), 400
        
        stats = rag_pipeline.get_conversation_stats()
        stats['status'] = 'success'
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        'service': 'Law 6331 RAG System API',
        'version': '1.0.0',
        'mongodb': 'MongoDB Atlas Vector Search',
        'endpoints': {
            'POST /api/ask': 'Submit a question (JSON body: {"question": "..."})',
            'POST /api/reset': 'Reset conversation history',
            'GET /api/memory': 'Get conversation memory statistics',
            'GET /health': 'Health check',
            'GET /stats': 'Database statistics'
        },
        'features': {
            'smart_memory': 'Sliding window conversation history (max 10 messages)',
            'vector_search': 'MongoDB Atlas Vector Search',
            'reranking': 'Intelligent document reranking'
        }
    }), 200


if __name__ == '__main__':
    # Initialize RAG system on startup
    initialize_rag_system()
    
    # Run Flask app
    # Railway will set the PORT environment variable
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
