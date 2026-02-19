# Legislation RAG System

AI-powered legal document search and question answering system using MongoDB Atlas Vector Search and Retrieval-Augmented Generation (RAG).

##  Features

- **Vector Search**: MongoDB Atlas Vector Search for semantic document retrieval
- **RAG Pipeline**: Advanced retrieval-augmented generation with query expansion
- **Reranking**: FlashRank for improved result quality
- **Turkish Support**: Optimized for Turkish legal documents
- **Scalable**: Railway deployment with MongoDB Atlas backend

##  Architecture

```
PDF Documents → Preprocessing → MongoDB Atlas (Vector DB)
                                      ↓
User Query → Query Expansion → Vector Search → Reranking → LLM → Answer
```

##  Tech Stack

- **Vector Database**: MongoDB Atlas with Vector Search
- **Embeddings**: Sentence Transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **LLM**: OpenRouter API (Jamba-mini)
- **Reranker**: FlashRank
- **API**: Flask + Gunicorn
- **Deployment**: Railway

##  Quick Start

### Prerequisites

- MongoDB Atlas account (free tier works)
- OpenRouter API key
- Python 3.11+

### Environment Variables

Create `.env` file:

```bash
# MongoDB Atlas
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=yourapp
MONGO_DB_NAME=legislation_db
MONGO_COLLECTION_NAME=documents
MONGO_VECTOR_INDEX_NAME=vector_index

# OpenRouter API
OPENROUTER_API_KEY=your_api_key

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run preprocessing (one-time)
python preprocessing_clean.py

# Start API server
python app.py
```

### Railway Deployment

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for detailed instructions.

## Data Processing

1. **Load PDFs**: Extract text from legal documents
2. **Chunk**: Split into 1000-character chunks with 200 overlap
3. **Embed**: Generate 384-dimensional vectors
4. **Upload**: Store in MongoDB Atlas with vector index

## 🔍 Query Flow

1. User submits question
2. Query expansion generates related queries
3. Vector search retrieves top-K documents
4. Reranker selects most relevant chunks
5. LLM generates answer with citations

##  Project Structure

```
.
├── app.py                    # Flask API server
├── preprocessing_clean.py    # Data ingestion script
├── rag_pipeline.py          # RAG orchestration
├── mongodb_vector_store.py  # MongoDB vector operations
├── document_loader.py       # PDF processing
├── query_expansion.py       # Query enhancement
├── reranker.py             # Result reranking
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
└── railway_start.sh        # Railway startup script
```

##  Configuration

Edit `config.py`:

- `CHUNK_SIZE`: Document chunk size (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200)
- `INITIAL_RETRIEVAL_K`: Initial search results (default: 50)
- `TOP_RERANKED_K`: Final reranked results (default: 15)
- `TEMPERATURE`: LLM temperature (default: 0.2)

##  API Endpoints

### Health Check
```bash
GET /health
```

### Query
```bash
POST /query
Content-Type: application/json

{
  "question": "What are the workplace safety regulations?"
}
```

Response:
```json
{
  "answer": "According to the regulations...",
  "sources": ["document1.pdf", "document2.pdf"],
  "confidence": 0.95
}
```

##  Development

### Add New Documents

1. Place PDF files in `data/` directory
2. Run preprocessing:
   ```bash
   python preprocessing_clean.py
   ```

### Test Locally

```bash
# Test MongoDB connection
python -c "from mongodb_vector_store import MongoDBVectorStore; store = MongoDBVectorStore(); print(' Connected')"

# Test API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test question"}'
```

##  Documentation

- [Railway Deployment Guide](RAILWAY_DEPLOYMENT.md)
- [Quick Start Guide](QUICK_START.md)

##  Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

##  License

This project is licensed under the MIT License.

##  Acknowledgments

- MongoDB Atlas for vector search capabilities
- Sentence Transformers for multilingual embeddings
- OpenRouter for LLM API access
- FlashRank for efficient reranking

---

**Built with ❤️ for legal professionals**
