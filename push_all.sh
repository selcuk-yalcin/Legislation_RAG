#!/bin/bash
cd /Users/selcuk/Desktop/admin_pan/Legislation_RAG
echo "=== STEP 1: git add -A ==="
git add -A
echo "=== STEP 2: git commit ==="
git commit -m "chore: sync all files - Denetci modu prompt + temp 0.1 + max_tokens 800"
echo "=== STEP 3: git push ==="
git push origin main
echo "=== STEP 4: update parent repo ==="
cd /Users/selcuk/Desktop/admin_pan
git add Legislation_RAG
git commit -m "chore: update Legislation_RAG submodule - Denetci modu"
git push origin main
echo "=== ALL DONE ==="
