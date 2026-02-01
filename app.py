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
from reranker import RerankerService
from rag_pipeline import RAGPipeline

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


def initialize_rag_system():
    """Initialize the RAG system components"""
    global rag_pipeline
    
    if rag_pipeline is not None:
        return  # Already initialized
    
    print("🚀 Initializing Legislation RAG System (MongoDB)...\n")
    
    # 1. MongoDB'de veri var mı kontrol et
    if not mongodb_store_exists():
        print("❌ MongoDB'de döküman bulunamadı!")
        raise Exception("MongoDB'de döküman yok. Lütfen preprocessing.py scriptini çalıştırın.")
    
    # 2. Create OpenRouter client
    client = create_openrouter_client()
    
    # 3. MongoDB Vector Store'u yükle (ChromaDB yerine)
    vectorstore = get_mongodb_vectorstore()
    stats = vectorstore.get_collection_stats()
    print(f"✅ MongoDB bağlantısı başarılı: {stats['total_documents']} döküman yüklü\n")
    
    # 4. Initialize reranker
    reranker = RerankerService()
    
    # 5. Create RAG pipeline
    rag_pipeline = RAGPipeline(client, vectorstore, reranker)
    
    print("\n✅ Legislation RAG system ready!\n")


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
            'mongodb': health
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


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
        
        # Generate answer
        answer = rag_pipeline.generate_response(question)
        
        return jsonify({
            'answer': answer,
            'sources': [],  # TODO: Extract sources from answer
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
