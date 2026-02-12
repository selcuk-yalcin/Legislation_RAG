"""
Azure Blob Storage Backup Manager
Automatically backs up processed guides to Azure Blob Storage
for cloud archiving and redundancy.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from azure.storage.blob import BlobServiceClient, ContentSettings
from config import AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER


class AzureBackupManager:
    """Manage backups of processed guides to Azure Blob Storage"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client"""
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("❌ AZURE_STORAGE_CONNECTION_STRING not set in environment")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_name = AZURE_STORAGE_CONTAINER
        
        # Create container if it doesn't exist
        try:
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            if not self.container_client.exists():
                self.container_client.create_container()
                print(f"✅ Created container: {self.container_name}")
            else:
                print(f"✅ Container exists: {self.container_name}")
        except Exception as e:
            print(f"❌ Container error: {e}")
            raise
    
    def upload_file(
        self, 
        local_path: str, 
        blob_name: Optional[str] = None,
        overwrite: bool = True
    ) -> str:
        """
        Upload a file to Azure Blob Storage.
        
        Args:
            local_path: Path to local file
            blob_name: Name in blob storage (defaults to filename)
            overwrite: Whether to overwrite existing blob
            
        Returns:
            URL of uploaded blob
        """
        if not blob_name:
            blob_name = Path(local_path).name
        
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        # Set content type based on file extension
        content_type = self._get_content_type(local_path)
        content_settings = ContentSettings(content_type=content_type)
        
        with open(local_path, "rb") as data:
            blob_client.upload_blob(
                data, 
                overwrite=overwrite,
                content_settings=content_settings
            )
        
        return blob_client.url
    
    def upload_directory(
        self, 
        local_dir: str, 
        blob_prefix: str = "",
        file_extensions: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Upload entire directory to blob storage.
        
        Args:
            local_dir: Local directory path
            blob_prefix: Prefix for blob names (like a folder)
            file_extensions: Only upload files with these extensions (e.g., ['.json', '.md'])
            
        Returns:
            Dict mapping local path to blob URL
        """
        uploaded = {}
        local_path = Path(local_dir)
        
        if not local_path.exists():
            print(f"❌ Directory not found: {local_dir}")
            return uploaded
        
        # Get all files
        files = []
        if file_extensions:
            for ext in file_extensions:
                files.extend(local_path.rglob(f"*{ext}"))
        else:
            files = [f for f in local_path.rglob("*") if f.is_file()]
        
        print(f"\n📤 Uploading {len(files)} files to Azure...")
        
        for file_path in files:
            # Create blob name preserving directory structure
            relative_path = file_path.relative_to(local_path)
            blob_name = str(Path(blob_prefix) / relative_path) if blob_prefix else str(relative_path)
            
            try:
                url = self.upload_file(str(file_path), blob_name)
                uploaded[str(file_path)] = url
                print(f"   ✅ {file_path.name} → {blob_name}")
            except Exception as e:
                print(f"   ❌ Failed {file_path.name}: {e}")
        
        return uploaded
    
    def upload_json_data(
        self, 
        data: dict, 
        blob_name: str,
        overwrite: bool = True
    ) -> str:
        """
        Upload JSON data directly to blob storage.
        
        Args:
            data: Python dict to upload as JSON
            blob_name: Name in blob storage
            overwrite: Whether to overwrite existing blob
            
        Returns:
            URL of uploaded blob
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        content_settings = ContentSettings(content_type='application/json')
        
        blob_client.upload_blob(
            json_str.encode('utf-8'), 
            overwrite=overwrite,
            content_settings=content_settings
        )
        
        return blob_client.url
    
    def list_blobs(self, prefix: str = "") -> List[str]:
        """
        List all blobs in container with optional prefix.
        
        Args:
            prefix: Only list blobs starting with this prefix
            
        Returns:
            List of blob names
        """
        blobs = self.container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
    
    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob from storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            print(f"🗑️  Deleted: {blob_name}")
            return True
        except Exception as e:
            print(f"❌ Delete failed {blob_name}: {e}")
            return False
    
    def create_backup_snapshot(
        self, 
        guides_output_dir: str = "./guides_output",
        include_timestamp: bool = True
    ) -> Dict[str, str]:
        """
        Create complete backup snapshot of guides_output directory.
        
        Args:
            guides_output_dir: Local directory with exports
            include_timestamp: Add timestamp to blob prefix
            
        Returns:
            Backup metadata
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_prefix = f"backups/{timestamp}" if include_timestamp else "latest"
        
        print("\n" + "=" * 80)
        print("☁️  CREATING AZURE BACKUP SNAPSHOT")
        print("=" * 80)
        print(f"Local dir: {guides_output_dir}")
        print(f"Azure prefix: {blob_prefix}")
        
        # Upload all files
        uploaded = self.upload_directory(
            guides_output_dir,
            blob_prefix=blob_prefix
        )
        
        # Create metadata file
        metadata = {
            "timestamp": timestamp,
            "backup_time": datetime.now().isoformat(),
            "file_count": len(uploaded),
            "files": list(uploaded.values()),
            "blob_prefix": blob_prefix,
            "container": self.container_name
        }
        
        # Upload metadata
        metadata_blob = f"{blob_prefix}/backup_metadata.json"
        metadata_url = self.upload_json_data(metadata, metadata_blob)
        
        print(f"\n✅ Backup complete!")
        print(f"   Files: {len(uploaded)}")
        print(f"   Location: {self.container_name}/{blob_prefix}")
        print(f"   Metadata: {metadata_url}")
        
        return metadata
    
    def _get_content_type(self, file_path: str) -> str:
        """Get MIME type for file"""
        ext = Path(file_path).suffix.lower()
        content_types = {
            '.json': 'application/json',
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.html': 'text/html'
        }
        return content_types.get(ext, 'application/octet-stream')


def main():
    """Test Azure backup functionality"""
    print("\n" + "=" * 80)
    print("🧪 TESTING AZURE BACKUP MANAGER")
    print("=" * 80)
    
    try:
        manager = AzureBackupManager()
        
        # List existing backups
        print("\n📋 Existing backups:")
        backups = manager.list_blobs(prefix="backups/")
        for blob in backups[:10]:  # Show first 10
            print(f"   - {blob}")
        
        if backups:
            print(f"   ... ({len(backups)} total)")
        else:
            print("   (none)")
        
        # Check if guides_output exists
        guides_dir = Path("./guides_output")
        if guides_dir.exists():
            print(f"\n✅ Found local exports: {guides_dir.absolute()}")
            
            # Ask to create backup
            response = input("\n🤔 Create backup snapshot? (y/n): ").strip().lower()
            if response == 'y':
                metadata = manager.create_backup_snapshot()
                print(f"\n📊 Backup metadata:")
                print(json.dumps(metadata, indent=2, ensure_ascii=False))
        else:
            print(f"\n⚠️  No local exports found at: {guides_dir.absolute()}")
            print("   Run 'python export_guides.py' first")
    
    except ValueError as e:
        print(f"\n❌ {e}")
        print("\n💡 To use Azure backup, add to .env:")
        print("   AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...")
        print("   AZURE_STORAGE_CONTAINER=klavuzlar-backup")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
