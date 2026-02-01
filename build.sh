#!/bin/bash
set -e

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🔧 Setting up models (pre-downloading)..."
python setup_models.py

echo "✅ Build complete!"
