# Quick Start Guide

Get your Legislation RAG system running in 15 minutes.

## Step 1: MongoDB Atlas Setup (5 minutes)

### 1.1 Create Account
1. Go to https://www.mongodb.com/cloud/atlas/register
2. Sign up (free tier available)
3. Create a free M0 cluster:
   - Cloud Provider: AWS
   - Region: Frankfurt (eu-central-1)
   - Cluster Name: `legislations`

### 1.2 Create Database
1. Click **Database** → **Browse Collections**
2. Click **Create Database**:
   - Database name: `legislation_db`
   - Collection name: `documents`

### 1.3 Create User
1. Go to **Database Access** → **Add New Database User**
2. Set credentials:
   - Username: `your_username`
   - Password: Strong password (save it!)
   - Privileges: **Read and write to any database**

### 1.4 Allow Network Access
1. Go to **Network Access** → **Add IP Address**
2. Select **Allow Access from Anywhere** (0.0.0.0/0)
3. Click **Confirm**

### 1.5 Get Connection String
1. Click **Database** → **Connect**
2. Select **Drivers** → **Python**
3. Copy connection string (format below)

## Step 2: Local Setup (5 minutes)

### 2.1 Clone Repository
```bash
git clone https://github.com/selcuk-yalcin/Legislation_RAG.git
cd Legislation_RAG
```

### 2.2 Create Environment File
Create `.env` file:
```bash
# MongoDB Atlas
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=legislations
MONGO_DB_NAME=legislation_db
MONGO_COLLECTION_NAME=documents
MONGO_VECTOR_INDEX_NAME=vector_index

# OpenRouter API
OPENROUTER_API_KEY=your_openrouter_api_key

# Models
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
MODEL_CACHE_DIR=./models
FLASHRANK_CACHE_DIR=./flashrank_cache
```

### 2.3 Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 3: Data Preprocessing (Railway Recommended)

### Option A: Railway (Recommended)

1. Go to https://railway.app
2. Click **New Project** → **Deploy from GitHub**
3. Select your repository
4. Add environment variables from `.env`
5. Add one more variable:
   ```
   PREPROCESSING_MODE=true
   ```
6. Deploy and watch logs
7. Wait 10-15 minutes for preprocessing to complete

### Option B: Local (If you have powerful machine)

```bash
python preprocessing_clean.py
```

**Note**: This will:
- Load 96 PDF files
- Create ~5000 document chunks
- Generate embeddings (384 dimensions each)
- Upload to MongoDB Atlas
- Takes 10-15 minutes

## Step 4: Create Vector Search Index (2 minutes)

1. Go to MongoDB Atlas → **Database** → **Search**
2. Click **Create Search Index** → **JSON Editor**
3. Configuration:
   - Index Name: `vector_index`
   - Database: `legislation_db`
   - Collection: `documents`

4. Paste this JSON:
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "metadata.source_file"
    }
  ]
}
```

5. Click **Create Search Index**
6. Wait for status to become **Active** (~2-5 minutes)

## Step 5: Run API (1 minute)

### Local
```bash
python app.py
```

### Railway
1. Update `railway.json`:
```json
{
  "deploy": {
    "startCommand": "gunicorn --config gunicorn_config.py app:app"
  }
}
```

2. Remove `PREPROCESSING_MODE` variable
3. Redeploy

## Step 6: Test (1 minute)

### Health Check
```bash
curl http://localhost:8000/health
```

### Query
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the workplace safety regulations?"}'
```

Expected response:
```json
{
  "answer": "According to the regulations...",
  "sources": ["document1.pdf", "document2.pdf"],
  "processing_time": 2.5
}
```

## 🎉 Success!

Your RAG system is now running!

## Next Steps

- Add more PDF documents to `data/` folder
- Customize prompts in `rag_pipeline.py`
- Adjust chunk size in `config.py`
- Monitor MongoDB Atlas metrics
- Scale Railway deployment

## Troubleshooting

### "SSL handshake failed"
- Check Network Access in MongoDB Atlas
- Ensure IP is whitelisted

### "No documents found"
- Verify PDF files are in `data/` folder
- Check preprocessing logs

### "Embedding model not found"
- Ensure `MODEL_CACHE_DIR` is writable
- Check internet connection for first-time download

## Support

- GitHub Issues: https://github.com/selcuk-yalcin/Legislation_RAG/issues
- Railway Docs: https://docs.railway.app
- MongoDB Docs: https://docs.mongodb.com

---

**Total Time: ~15 minutes** ⏱️
