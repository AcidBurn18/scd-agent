"""
Azure Storage Manager for SCD Documents
Handles uploading SCD documents to Azure St        \"\"\"
        Store SCD document in Azure Storage with versioning
        
        Args:
            azure_service: Name of the Azure service
            scd_content: The SCD document content
            session_id: User session identifier
            additional_context: Additional context for metadata
            collected_data: Collected data for versioning hash
            operation_type: Type of operation (generation, refinement, manual_save)
            custom_filename: Custom filename to use (optional)
        
        Returns:
            dict: Storage result with URL, blob name, and metadata
        \"\"\"
        try:
            # Generate timestamp and blob name
            timestamp = datetime.utcnow().strftime(\"%Y-%m-%d_%H-%M-%S\")
            
            if custom_filename:
                # Use custom filename but ensure it's in the right folder structure
                clean_service = azure_service.replace(\" \", \"_\").replace(\"/\", \"_\").lower()
                blob_name = f\"{clean_service}/{session_id}/{custom_filename}\"
            else:
                blob_name = self._generate_blob_name(azure_service, session_id, timestamp)
            
            # Calculate hash for versioning
            data_hash = self._calculate_data_hash(collected_data) if collected_data else \"no-data\"
            
            # Generate metadata with operation type
            metadata = self._generate_metadata(
                azure_service, session_id, additional_context, data_hash, operation_type
            )rsioning
"""
import os
import json
from datetime import datetime
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.identity import DefaultAzureCredential
import hashlib

class SCDStorageManager:
    def __init__(self):
        """Initialize Azure Storage client"""
        self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scd-documents")
        
        if not self.storage_account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME environment variable is required")
        
        # Use account URL with DefaultAzureCredential
        account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
        
        try:
            # Try connection string first if available
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            else:
                # Use DefaultAzureCredential for authentication
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=DefaultAzureCredential()
                )
        except Exception as e:
            print(f"Failed to initialize Azure Storage client: {e}")
            raise
        
        # Ensure container exists
        self._ensure_container()

    def _ensure_container(self):
        """Ensure the SCD container exists"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                print(f"Created container: {self.container_name}")
            else:
                print(f"Container exists: {self.container_name}")
        except Exception as e:
            print(f"Error ensuring container: {e}")

    def _generate_blob_name(self, azure_service: str, session_id: str, timestamp: str) -> str:
        """Generate standardized blob name with versioning"""
        # Clean service name for file naming
        clean_service = azure_service.replace(" ", "_").replace("/", "_").lower()
        clean_session = session_id.replace(" ", "_").replace("/", "_")
        
        # Format: service/session_id/YYYY-MM-DD_HH-MM-SS_service-name.md
        blob_name = f"{clean_service}/{clean_session}/{timestamp}_{clean_service}_scd.md"
        return blob_name

    def _generate_metadata(self, azure_service: str, session_id: str, additional_context: str, 
                          collected_data_hash: str, operation_type: str = "generation") -> dict:
        """Generate metadata for the blob"""
        return {
            "azure_service": azure_service,
            "session_id": session_id,
            "additional_context": additional_context or "",
            "generated_timestamp": datetime.utcnow().isoformat(),
            "collected_data_hash": collected_data_hash,
            "document_type": "security_control_documentation",
            "format": "markdown",
            "version": "1.0",
            "operation_type": operation_type
        }

    def _calculate_data_hash(self, collected_data: str) -> str:
        """Calculate hash of collected data for versioning"""
        return hashlib.sha256(collected_data.encode('utf-8')).hexdigest()[:16]

    def store_scd(self, azure_service: str, scd_content: str, session_id: str = "default",
                  additional_context: str = "", collected_data: str = "", 
                  operation_type: str = "generation", custom_filename: str = None) -> dict:
        """
        Store SCD document in Azure Storage with versioning
        
        Returns:
            dict: Storage result with URL, blob name, and metadata
        """
        try:
            # Generate timestamp and blob name
            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            blob_name = self._generate_blob_name(azure_service, session_id, timestamp)
            
            # Calculate hash for versioning
            data_hash = self._calculate_data_hash(collected_data) if collected_data else "no-data"
            
            # Generate metadata
            metadata = self._generate_metadata(
                azure_service, session_id, additional_context, data_hash
            )
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload the SCD content
            blob_client.upload_blob(
                scd_content,
                overwrite=True,
                metadata=metadata,
                content_type="text/markdown"
            )
            
            # Get blob URL
            blob_url = blob_client.url
            
            print(f"SCD stored successfully: {blob_name}")
            
            return {
                "success": True,
                "blob_name": blob_name,
                "blob_url": blob_url,
                "container_name": self.container_name,
                "metadata": metadata,
                "storage_account": self.storage_account_name
            }
            
        except Exception as e:
            print(f"Error storing SCD: {e}")
            return {
                "success": False,
                "error": str(e),
                "blob_name": None,
                "blob_url": None
            }