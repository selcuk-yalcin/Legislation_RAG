"""
Simple Flask server for testing Admin Panel connection
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        count = collection.count_documents({})
        client.close()
        
        return jsonify({
            'status': 'healthy',
            'message': 'Legislation RAG API is running',
            'mongodb': {
                'connected': True,
                'documents': count
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Get database statistics"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        
        total_docs = collection.count_documents({})
        
        # Get unique source files
        pipeline = [
            {"$group": {"_id": "$metadata.source_file"}},
            {"$count": "total_files"}
        ]
        result = list(collection.aggregate(pipeline))
        total_files = result[0]['total_files'] if result else 0
        
        client.close()
        
        return jsonify({
            'status': 'success',
            'total_documents': total_docs,
            'total_chunks': total_docs,
            'total_files': total_files,
            'database': MONGO_DB_NAME,
            'collection': MONGO_COLLECTION_NAME
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'total_documents': 0,
            'total_chunks': 0
        }), 500

@app.route('/query', methods=['POST', 'OPTIONS'])
def query():
    """Simple query endpoint"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({
                'status': 'error',
                'error': 'Question is required'
            }), 400
        
        # For now, return a simple response
        # TODO: Implement full RAG pipeline
        return jsonify({
            'status': 'success',
            'answer': f'Sorunuz alındı: "{question}". RAG pipeline yakında entegre edilecek. Şu anda MongoDB\'de {get_doc_count()} döküman mevcut.',
            'sources': []
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'answer': 'Bir hata oluştu.'
        }), 500

@app.route('/reset', methods=['POST', 'OPTIONS'])
def reset():
    """Reset conversation"""
    if request.method == 'OPTIONS':
        return '', 204
    
    return jsonify({
        'status': 'success',
        'message': 'Conversation reset'
    }), 200

def get_doc_count():
    """Get document count from MongoDB"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        count = collection.count_documents({})
        client.close()
        return count
    except:
        return 0

if __name__ == '__main__':
    print("🚀 Starting Simple Legislation API Server...")
    print(f"📊 MongoDB: {MONGO_DB_NAME}")
    print(f"📁 Collection: {MONGO_COLLECTION_NAME}")
    print("🔗 Server running on http://localhost:8000")
    app.run(debug=True, host='0.0.0.0', port=8000)
