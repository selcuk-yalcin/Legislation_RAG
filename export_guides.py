"""
Guides Export Tool
Exports processed guides from MongoDB to JSON and Markdown formats
for easy inspection and backup.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME


class GuidesExporter:
    """Export guides from MongoDB to JSON/Markdown files"""
    
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB_NAME]
        self.collection = self.db["guides"]
        
        # Create output directories
        self.output_dir = Path("./guides_output")
        self.json_dir = self.output_dir / "json"
        self.md_dir = self.output_dir / "markdown"
        
        for dir_path in [self.output_dir, self.json_dir, self.md_dir]:
            dir_path.mkdir(exist_ok=True)
        
        print(f"✅ Exporter initialized")
        print(f"   Output: {self.output_dir.absolute()}")
    
    def export_all_to_json(self, include_embeddings: bool = False):
        """
        Export all guides to JSON files (one file per guide).
        
        Args:
            include_embeddings: Include 1024-dim embeddings (makes files large)
        """
        print("\n" + "=" * 80)
        print("📄 EXPORTING TO JSON")
        print("=" * 80)
        
        # Get all unique guide titles
        pipeline = [
            {"$group": {
                "_id": "$metadata.guide_title",
                "source_file": {"$first": "$metadata.source_file"},
                "chunk_count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        guides = list(self.collection.aggregate(pipeline))
        print(f"\n📚 Found {len(guides)} unique guides")
        
        for idx, guide in enumerate(guides, 1):
            guide_title = guide["_id"]
            source_file = guide["source_file"]
            chunk_count = guide["chunk_count"]
            
            print(f"\n[{idx}/{len(guides)}] {guide_title}")
            print(f"   Chunks: {chunk_count}")
            
            # Get all chunks for this guide
            chunks = list(self.collection.find(
                {"metadata.guide_title": guide_title},
                {"_id": 0}  # Exclude MongoDB _id
            ).sort("metadata.chunk_index", 1))
            
            # Prepare export data
            export_data = {
                "guide_title": guide_title,
                "source_file": source_file,
                "total_chunks": chunk_count,
                "exported_at": datetime.now().isoformat(),
                "chunks": []
            }
            
            for chunk in chunks:
                # Convert metadata, handling datetime objects
                metadata_copy = {}
                for key, value in chunk["metadata"].items():
                    if isinstance(value, datetime):
                        metadata_copy[key] = value.isoformat()
                    else:
                        metadata_copy[key] = value
                
                chunk_data = {
                    "chunk_index": chunk["metadata"]["chunk_index"],
                    "content": chunk["content"],
                    "metadata": metadata_copy
                }
                
                # Optionally include embeddings (convert to list if needed)
                if include_embeddings and "embedding" in chunk:
                    emb = chunk["embedding"]
                    chunk_data["embedding"] = list(emb) if not isinstance(emb, list) else emb
                
                export_data["chunks"].append(chunk_data)
            
            # Save to JSON file
            safe_filename = guide_title.replace("/", "-").replace("\\", "-")[:100]
            json_path = self.json_dir / f"{safe_filename}.json"
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            file_size = json_path.stat().st_size / 1024
            print(f"   ✅ Saved: {json_path.name} ({file_size:.1f} KB)")
        
        print(f"\n✅ JSON export complete: {len(guides)} files")
        print(f"   Location: {self.json_dir.absolute()}")
    
    def export_all_to_markdown(self):
        """
        Export all guides to Markdown files (one file per guide).
        Each file contains all chunks concatenated with headers.
        """
        print("\n" + "=" * 80)
        print("📝 EXPORTING TO MARKDOWN")
        print("=" * 80)
        
        # Get all unique guide titles
        pipeline = [
            {"$group": {
                "_id": "$metadata.guide_title",
                "source_file": {"$first": "$metadata.source_file"},
                "chunk_count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        guides = list(self.collection.aggregate(pipeline))
        print(f"\n📚 Found {len(guides)} unique guides")
        
        for idx, guide in enumerate(guides, 1):
            guide_title = guide["_id"]
            source_file = guide["source_file"]
            chunk_count = guide["chunk_count"]
            
            print(f"\n[{idx}/{len(guides)}] {guide_title}")
            
            # Get all chunks for this guide (sorted by chunk_index)
            chunks = list(self.collection.find(
                {"metadata.guide_title": guide_title}
            ).sort("metadata.chunk_index", 1))
            
            # Build markdown content
            md_content = f"""# {guide_title}

**Source File:** `{source_file}`  
**Total Chunks:** {chunk_count}  
**Exported:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""
            
            # Add each chunk
            for chunk in chunks:
                chunk_idx = chunk["metadata"]["chunk_index"]
                content = chunk["content"]
                
                md_content += f"""
## Chunk {chunk_idx + 1}/{chunk_count}

{content}

---

"""
            
            # Save to markdown file
            safe_filename = guide_title.replace("/", "-").replace("\\", "-")[:100]
            md_path = self.md_dir / f"{safe_filename}.md"
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            file_size = md_path.stat().st_size / 1024
            print(f"   ✅ Saved: {md_path.name} ({file_size:.1f} KB)")
        
        print(f"\n✅ Markdown export complete: {len(guides)} files")
        print(f"   Location: {self.md_dir.absolute()}")
    
    def export_summary(self):
        """
        Export a summary of all guides (single JSON file).
        """
        print("\n" + "=" * 80)
        print("📊 EXPORTING SUMMARY")
        print("=" * 80)
        
        # Get all guides with stats
        pipeline = [
            {"$group": {
                "_id": "$metadata.guide_title",
                "source_file": {"$first": "$metadata.source_file"},
                "chunk_count": {"$sum": 1},
                "total_chars": {"$sum": {"$strLenCP": "$content"}},
                "processed_at": {"$first": "$metadata.processed_at"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        guides = list(self.collection.aggregate(pipeline))
        
        summary = {
            "export_date": datetime.now().isoformat(),
            "total_guides": len(guides),
            "total_chunks": sum(g["chunk_count"] for g in guides),
            "total_characters": sum(g["total_chars"] for g in guides),
            "guides": []
        }
        
        for guide in guides:
            summary["guides"].append({
                "title": guide["_id"],
                "source_file": guide["source_file"],
                "chunks": guide["chunk_count"],
                "characters": guide["total_chars"],
                "processed_at": guide["processed_at"].isoformat() if guide.get("processed_at") else None
            })
        
        # Save summary
        summary_path = self.output_dir / "guides_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 Summary Statistics:")
        print(f"   Total Guides: {summary['total_guides']}")
        print(f"   Total Chunks: {summary['total_chunks']}")
        print(f"   Total Characters: {summary['total_characters']:,}")
        print(f"\n✅ Summary saved: {summary_path.absolute()}")
    
    def export_sample_chunks(self, limit: int = 5):
        """
        Export sample chunks for inspection (JSON format).
        """
        print("\n" + "=" * 80)
        print(f"🔍 EXPORTING {limit} SAMPLE CHUNKS")
        print("=" * 80)
        
        samples = list(self.collection.find(
            {},
            {"_id": 0}
        ).limit(limit))
        
        # Helper function to recursively convert datetime objects
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            else:
                return obj
        
        # Process each sample
        processed_samples = []
        for sample in samples:
            if "embedding" in sample:
                sample["embedding"] = f"[{len(sample['embedding'])} dimensions - truncated]"
            
            # Recursively convert all datetime objects
            sample = convert_datetime(sample)
            processed_samples.append(sample)
        
        sample_path = self.output_dir / "sample_chunks.json"
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(processed_samples, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Sample saved: {sample_path.absolute()}")
        
        # Print first sample
        if processed_samples:
            print(f"\n📄 First Sample:")
            print(f"   Title: {processed_samples[0]['metadata']['guide_title']}")
            print(f"   Chunk: {processed_samples[0]['metadata']['chunk_index']}")
            print(f"   Content (first 200 chars):")
            print(f"   {processed_samples[0]['content'][:200]}...")
    
    def run_full_export(self, include_embeddings: bool = False):
        """
        Run all export operations.
        
        Args:
            include_embeddings: Include embeddings in JSON export
        """
        print("=" * 80)
        print("📦 GUIDES FULL EXPORT")
        print("=" * 80)
        
        total_docs = self.collection.count_documents({})
        print(f"\n📊 MongoDB Collection: {total_docs:,} chunks")
        
        if total_docs == 0:
            print("\n⚠️  No guides found in MongoDB!")
            print("   Run upload_klavuzlar_with_azure.py first")
            return
        
        # Export everything
        self.export_summary()
        self.export_all_to_json(include_embeddings=include_embeddings)
        self.export_all_to_markdown()
        self.export_sample_chunks(limit=5)
        
        print("\n" + "=" * 80)
        print("✅ FULL EXPORT COMPLETE!")
        print("=" * 80)
        print(f"\n📂 Output Directory: {self.output_dir.absolute()}")
        print(f"""
📁 Directory Structure:
   guides_output/
   ├── guides_summary.json        (Overview of all guides)
   ├── sample_chunks.json          (5 sample chunks for inspection)
   ├── json/                       (Individual guide JSON files)
   │   ├── guide1.json
   │   ├── guide2.json
   │   └── ...
   └── markdown/                   (Individual guide Markdown files)
       ├── guide1.md
       ├── guide2.md
       └── ...
""")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  GUIDES EXPORT TOOL                                            ║
    ║                                                                ║
    ║  Exports MongoDB guides to:                                    ║
    ║  1. JSON files (one per guide, structured data)               ║
    ║  2. Markdown files (one per guide, human-readable)            ║
    ║  3. Summary file (statistics and overview)                    ║
    ║  4. Sample chunks (for inspection)                            ║
    ║  5. Azure Blob Storage backup (cloud archive)                 ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    exporter = GuidesExporter()
    
    # Ask user preference
    print("\n📋 Export Options:")
    print("1. Full export (JSON + Markdown + Summary + Azure Backup)")
    print("2. JSON only")
    print("3. Markdown only")
    print("4. Summary only")
    print("5. Sample chunks only")
    print("6. Azure Backup only (upload existing exports)")
    
    choice = input("\nSelect option (1-6, default=1): ").strip() or "1"
    
    include_embeddings = False
    if choice in ["1", "2"]:
        response = input("Include embeddings in JSON? (y/n, default=n): ").strip().lower()
        include_embeddings = response == "y"
    
    print("\n" + "=" * 80)
    
    if choice == "1":
        exporter.run_full_export(include_embeddings=include_embeddings)
        
        # Ask for Azure backup
        print("\n" + "=" * 80)
        azure_response = input("\n☁️  Upload to Azure Blob Storage? (y/n, default=y): ").strip().lower() or "y"
        
        if azure_response == "y":
            try:
                from azure_backup_manager import AzureBackupManager
                backup_manager = AzureBackupManager()
                metadata = backup_manager.create_backup_snapshot()
                
                print("\n✅ AZURE BACKUP COMPLETE!")
                print(f"   Container: {metadata['container']}")
                print(f"   Location: {metadata['blob_prefix']}")
                print(f"   Files: {metadata['file_count']}")
                
            except ImportError:
                print("\n⚠️  Azure backup unavailable (install: pip install azure-storage-blob)")
            except ValueError as e:
                print(f"\n⚠️  {e}")
                print("   Add AZURE_STORAGE_CONNECTION_STRING to .env to enable backup")
            except Exception as e:
                print(f"\n❌ Backup failed: {e}")
        
    elif choice == "2":
        exporter.export_all_to_json(include_embeddings=include_embeddings)
    elif choice == "3":
        exporter.export_all_to_markdown()
    elif choice == "4":
        exporter.export_summary()
    elif choice == "5":
        exporter.export_sample_chunks(limit=10)
    elif choice == "6":
        # Azure backup only
        try:
            from azure_backup_manager import AzureBackupManager
            backup_manager = AzureBackupManager()
            metadata = backup_manager.create_backup_snapshot()
            
            print("\n✅ AZURE BACKUP COMPLETE!")
            print(f"   Container: {metadata['container']}")
            print(f"   Location: {metadata['blob_prefix']}")
            print(f"   Files: {metadata['file_count']}")
            
        except ImportError:
            print("\n⚠️  Azure backup unavailable")
            print("   Install: pip install azure-storage-blob")
        except ValueError as e:
            print(f"\n⚠️  {e}")
            print("   Add AZURE_STORAGE_CONNECTION_STRING to .env to enable backup")
        except Exception as e:
            print(f"\n❌ Backup failed: {e}")
    else:
        print("❌ Invalid option")
