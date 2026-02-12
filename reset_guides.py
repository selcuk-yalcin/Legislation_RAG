"""
Quick script to reset guides collection for fresh upload
"""
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db["guides"]

# Count before
before_count = collection.count_documents({})
print(f"📊 Before: {before_count} chunks in guides collection")

# Delete all
if before_count > 0:
    response = input(f"\n⚠️  Delete all {before_count} chunks? (y/n): ").strip().lower()
    if response == 'y':
        result = collection.delete_many({})
        print(f"🗑️  Deleted {result.deleted_count} chunks")
        print("✅ Guides collection is now empty - ready for fresh upload")
    else:
        print("❌ Cancelled")
else:
    print("✅ Collection already empty")
