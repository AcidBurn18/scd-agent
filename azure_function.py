"""
Azure Function - Blob Storage Trigger for SCD Generation
Triggered automatically when JSON request files are uploaded to storage
"""
import json
import logging
import os
from datetime import datetime
import azure.functions as func

# Set UTF-8 encoding for Windows compatibility
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Import dependencies with error handling
SCDGenerator = None
GitHubIntegrator = None

try:
    from scd_generator import SCDGenerator
    logging.info("[SUCCESS] SCDGenerator imported successfully")
except ImportError as e:
    logging.error(f"[ERROR] Failed to import SCDGenerator: {e}")
    SCDGenerator = None

try:
    from github_integration import GitHubIntegrator
    logging.info("[SUCCESS] GitHubIntegrator imported successfully")
except ImportError as e:
    logging.error(f"[ERROR] Failed to import GitHubIntegrator: {e}")
    GitHubIntegrator = None

# Create a function app instance
app = func.FunctionApp()

# Global progress tracking (for monitoring)
progress_tracker = {}

def update_progress(request_id: str, step: str, percentage: int, description: str):
    """Update progress for a request"""
    progress_tracker[request_id] = {
        'step': step,
        'percentage': percentage,
        'description': description,
        'timestamp': datetime.utcnow().isoformat()
    }
    logging.info(f"[PROGRESS] {request_id}: {percentage}% - {step} - {description}")

@app.blob_trigger(
    arg_name="myblob", 
    path="scd-requests/{name}",
    connection="AzureWebJobsStorage"
)
def scd_blob_processor(myblob: func.InputStream) -> None:
    """
    Process SCD generation requests from blob storage uploads
    Triggered when JSON files are uploaded to 'scd-requests' container
    """
    try:
        request_id = f"req_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{myblob.name.split('/')[-1].replace('.json', '')}"
        
        logging.info(f"[BLOB TRIGGER] Processing request: {myblob.name}, Request ID: {request_id}")
        update_progress(request_id, 'started', 5, f'Processing blob: {myblob.name}')
        
        # Read and parse JSON request
        blob_content = myblob.read().decode('utf-8')
        request_data = json.loads(blob_content)
        
        logging.info(f"[REQUEST] Parsed JSON request: {json.dumps(request_data, indent=2)}")
        update_progress(request_id, 'parsing', 10, 'JSON request parsed successfully')
        
        # Validate required fields
        required_fields = ['azure_service']
        missing_fields = [field for field in required_fields if field not in request_data]
        
        if missing_fields:
            error_msg = f"Missing required fields: {missing_fields}"
            logging.error(f"[VALIDATION ERROR] {error_msg}")
            
            # Store error result
            store_error_result(request_id, error_msg, myblob.name)
            return
        
        # Extract request parameters
        azure_service = request_data['azure_service']
        additional_context = request_data.get('additional_context', '')
        auto_collect = request_data.get('auto_collect', True)
        store_in_azure = request_data.get('store_in_azure', True)
        github_integration = request_data.get('github_integration', {})
        
        logging.info(f"[REQUEST PARAMS] Service: {azure_service}, Auto-collect: {auto_collect}, Store: {store_in_azure}")
        update_progress(request_id, 'validated', 15, f'Request validated for service: {azure_service}')
        
        # Check if dependencies are available
        if SCDGenerator is None:
            error_msg = "SCDGenerator module not available - missing dependencies"
            logging.error(f"[DEPENDENCY ERROR] {error_msg}")
            store_error_result(request_id, error_msg, myblob.name)
            return
        
        # Initialize SCD Generator
        update_progress(request_id, 'initializing', 20, 'Initializing SCD Generator')
        generator = SCDGenerator(progress_callback=lambda sid, step, pct, desc: update_progress(request_id, step, pct, desc))
        
        # Generate SCD
        update_progress(request_id, 'generating', 25, f'Starting SCD generation for {azure_service}')
        
        result = generator.generate_scd(
            azure_service=azure_service,
            additional_context=additional_context,
            session_id=request_id,
            store_in_azure=store_in_azure,
            auto_collect=auto_collect
        )
        
        # Check if generation failed (error is not None/empty)
        if result.get("error"):
            error_msg = result["error"]
            logging.error(f"[SCD GENERATION ERROR] {error_msg}")
            store_error_result(request_id, error_msg, myblob.name)
            return
        
        scd_content = result.get("scd_content")
        storage_info = result.get("storage_info")
        
        logging.info(f"[SCD RESULT] SCD Content length: {len(scd_content) if scd_content else 0}")
        logging.info(f"[SCD RESULT] Storage info: {storage_info}")
        logging.info(f"[GITHUB CHECK] GitHub integration enabled: {github_integration.get('enabled', False)}")
        logging.info(f"[GITHUB CHECK] SCD content available: {bool(scd_content)}")
        
        update_progress(request_id, 'scd_generated', 80, 'SCD generation completed successfully')
        
        # STEP 1: Ensure SCD is stored in Azure Storage (if not already done)
        update_progress(request_id, 'storing_scd', 85, 'Storing SCD in Azure Storage')
        
        if not storage_info and scd_content and store_in_azure:
            # If SCD wasn't stored during generation, store it now
            logging.info(f"[STORAGE] SCD not stored during generation, storing now...")
            try:
                from scd_storage_manager import SCDStorageManager
                storage_manager = SCDStorageManager()
                storage_result = storage_manager.store_scd(
                    azure_service=azure_service,
                    scd_content=scd_content,
                    session_id=request_id,
                    additional_context=additional_context,
                    collected_data=None,
                    operation_type="function_generation"
                )
                storage_info = storage_result
                logging.info(f"[STORAGE] SCD stored successfully: {storage_info}")
            except Exception as storage_error:
                logging.error(f"[STORAGE ERROR] Failed to store SCD: {str(storage_error)}")
                storage_info = {"error": str(storage_error)}
        
        # STEP 2: GitHub Integration (only after storage is confirmed)
        logging.info(f"[GITHUB] About to check GitHub integration...")
        github_result = None
        if github_integration.get('enabled', False) and scd_content:
            if GitHubIntegrator is None:
                logging.warning("[GITHUB WARNING] GitHub integration requested but GitHubIntegrator not available")
                github_result = {"error": "GitHubIntegrator module not available"}
            else:
                try:
                    # Wait a moment to ensure storage is complete
                    import time
                    time.sleep(1)
                    
                    update_progress(request_id, 'github_integration', 90, 'Creating GitHub branch and PR')
                    logging.info(f"[GITHUB] Starting GitHub integration for {azure_service}")
                    
                    github_integrator = GitHubIntegrator()
                    
                    # Verify GitHub is configured
                    if not github_integrator.is_configured():
                        github_result = {"success": False, "error": "GitHub integration not properly configured"}
                        logging.error(f"[GITHUB ERROR] Configuration incomplete")
                    else:
                        # Create branch and PR
                        github_result = github_integrator.create_branch_and_pr(
                            scd_content=scd_content,
                            service_name=azure_service,
                            session_id=request_id
                        )
                        
                        if github_result.get('success'):
                            logging.info(f"[GITHUB SUCCESS] PR created: {github_result.get('pr_url')}")
                        else:
                            logging.error(f"[GITHUB FAILED] {github_result.get('error')}")
                    
                    logging.info(f"[GITHUB] Integration result: {github_result}")
                    
                except Exception as github_error:
                    logging.error(f"[GITHUB ERROR] Exception during GitHub integration: {str(github_error)}")
                    github_result = {"success": False, "error": str(github_error)}
        
        # Store successful result
        final_result = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "azure_service": azure_service,
            "scd_content_length": len(scd_content) if scd_content else 0,
            "storage_info": storage_info,
            "github_integration": github_result,
            "original_request": request_data,
            "processing_blob": myblob.name
        }
        
        store_success_result(request_id, final_result, scd_content)
        update_progress(request_id, 'completed', 100, 'SCD generation completed successfully')
        
        logging.info(f"[SUCCESS] Request {request_id} completed successfully")
        
    except json.JSONDecodeError as json_error:
        error_msg = f"Invalid JSON format: {str(json_error)}"
        logging.error(f"[JSON ERROR] {error_msg}")
        store_error_result(f"error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}", error_msg, myblob.name)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.error(f"[UNEXPECTED ERROR] {error_msg}")
        store_error_result(f"error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}", error_msg, myblob.name)

def store_success_result(request_id: str, result_data: dict, scd_content: str):
    """Store successful result to blob storage"""
    try:
        from azure.storage.blob import BlobServiceClient
        
        # Get connection string
        connection_string = os.environ.get('AzureWebJobsStorage')
        if not connection_string:
            logging.warning("[STORAGE] No connection string found, skipping result storage")
            return
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Store result metadata
        result_container = "scd-results"
        result_blob_name = f"{request_id}/result.json"
        
        blob_client = blob_service_client.get_blob_client(
            container=result_container,
            blob=result_blob_name
        )
        
        blob_client.upload_blob(
            json.dumps(result_data, indent=2),
            overwrite=True,
            content_type="application/json"
        )
        
        # Store SCD content if available
        if scd_content:
            scd_blob_name = f"{request_id}/scd_content.md"
            scd_blob_client = blob_service_client.get_blob_client(
                container=result_container,
                blob=scd_blob_name
            )
            
            scd_blob_client.upload_blob(
                scd_content,
                overwrite=True,
                content_type="text/markdown"
            )
        
        logging.info(f"[STORAGE] Results stored for request {request_id}")
        
    except Exception as storage_error:
        logging.error(f"[STORAGE ERROR] Failed to store results: {str(storage_error)}")

def store_error_result(request_id: str, error_message: str, original_blob: str):
    """Store error result to blob storage"""
    try:
        from azure.storage.blob import BlobServiceClient
        
        # Get connection string
        connection_string = os.environ.get('AzureWebJobsStorage')
        if not connection_string:
            logging.warning("[STORAGE] No connection string found, skipping error storage")
            return
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Store error result
        error_container = "scd-errors"
        error_blob_name = f"{request_id}/error.json"
        
        error_data = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message,
            "original_blob": original_blob
        }
        
        blob_client = blob_service_client.get_blob_client(
            container=error_container,
            blob=error_blob_name
        )
        
        blob_client.upload_blob(
            json.dumps(error_data, indent=2),
            overwrite=True,
            content_type="application/json"
        )
        
        logging.info(f"[ERROR STORAGE] Error result stored for request {request_id}")
        
    except Exception as storage_error:
        logging.error(f"[ERROR STORAGE] Failed to store error: {str(storage_error)}")