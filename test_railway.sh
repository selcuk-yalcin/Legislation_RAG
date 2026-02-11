#!/bin/bash
# Railway Deployment Test Script
# Usage: ./test_railway.sh <railway-url>

RAILWAY_URL="${1:-https://legislation-rag-production.up.railway.app}"

echo "======================================================================"
echo "🚂 Railway Deployment Test"
echo "======================================================================"
echo "URL: $RAILWAY_URL"
echo ""

# Test 1: Health Check
echo "1️⃣ Health Check..."
curl -s "$RAILWAY_URL/health" | jq '.'
echo ""

# Test 2: Stats
echo "2️⃣ Database Stats..."
curl -s "$RAILWAY_URL/stats" | jq '.'
echo ""

# Test 3: Simple Query (Internal RAG)
echo "3️⃣ Simple Query (Internal RAG)..."
curl -s "$RAILWAY_URL/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "6331 sayılı kanun nedir"}' | jq '.answer' -r | head -20
echo ""

# Test 4: Web Fallback Query (will trigger Serper)
echo "4️⃣ Web Fallback Query (Serper + Azure DI + MongoDB)..."
curl -s "$RAILWAY_URL/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "2025 yılında isg yönetmeliklerinde yapılan değişiklikler"}' | jq '.'
echo ""

# Test 5: TR IP Check (mevzuat.gov.tr erişimi)
echo "5️⃣ TR IP Test (mevzuat.gov.tr)..."
curl -s "$RAILWAY_URL/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "yapı işlerinde isg yönetmeliği güncel hali"}' \
  | jq '.sources[] | select(.link | contains("mevzuat.gov.tr")) | .link' | head -3
echo ""

echo "======================================================================"
echo "✅ Test Tamamlandı"
echo "======================================================================"
