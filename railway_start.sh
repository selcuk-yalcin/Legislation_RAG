#!/bin/bash
# Railway Start Script
# MongoDB'de veriler zaten var, sadece API'yi başlat

echo "======================================================================"
echo "🚀 Railway Legislation RAG API"
echo "======================================================================"

# MongoDB bağlantısını kontrol et
echo ""
echo "1️⃣ MongoDB bağlantısı kontrol ediliyor..."
python -c "from config import MONGO_URI, MONGO_DB_NAME; from pymongo import MongoClient; client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000); client.server_info(); print('✅ MongoDB bağlantısı başarılı!'); client.close()"

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "✅ MongoDB hazır! (Veriler local'de yüklendi)"
    echo "======================================================================"
    echo ""
    echo "2️⃣ RAG API başlatılıyor..."
    
    # Gunicorn ile production server başlat
    gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --log-level info
else
    echo ""
    echo "❌ MongoDB bağlantı hatası! Environment variables kontrol edin."
    exit 1
fi
