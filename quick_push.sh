#!/bin/bash

# Quick Push Script - Push sadece kaynak kodları (model ve data hariç)

echo "🚀 GitHub'a push hazırlanıyor..."

cd /Users/selcuk/Desktop/admin_pan/Legislation_RAG

# Eğer .git yoksa yeni repo başlat
if [ ! -d ".git" ]; then
    echo "📦 Yeni git repository başlatılıyor..."
    git init
fi

# Sadece kaynak kod dosyalarını ekle
echo "📝 Dosyalar ekleniyor (model ve PDF'ler hariç)..."
git add .gitignore .dockerignore
git add *.py *.sh *.md *.txt *.json
git add Dockerfile Procfile
git add docs/ tests/
git add requirements.txt

echo "✅ Dosyalar hazır. Status:"
git status --short

echo ""
read -p "Commit mesajı: " commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="Update: MongoDB RAG system"
fi

git commit -m "$commit_msg"

echo ""
echo "🔗 Remote repository ekle/güncelle:"
echo "   git remote add origin https://github.com/selcuk-yalcin/Legislation_RAG.git"
echo ""
read -p "Push yapılsın mı? (y/n): " push_confirm

if [ "$push_confirm" = "y" ]; then
    git push -u origin main --force
    echo "✅ Push tamamlandı!"
else
    echo "⏸️  Push iptal edildi. Manuel push için:"
    echo "   git push -u origin main --force"
fi
