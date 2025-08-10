"""
Modern Webhook Handler using new modular architecture
Receives webhook notifications and triggers transcription jobs
"""

import json
import os
import asyncio
from typing import Dict, Any
from datetime import datetime

import functions_framework
from flask import Request

# Import our new modular services
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services import ServiceFactory, Settings
from services.webhook import WebhookService, CursorManager, JobTracker


# Global service instances (initialized on first use)
_webhook_service = None
_factory = None


def get_webhook_service() -> WebhookService:
    """
    Get or create webhook service instance
    
    Returns:
        Configured WebhookService instance
    """
    global _webhook_service, _factory
    
    if _webhook_service is None:
        print("🔧 Initializing webhook service...")
        
        # Create settings from environment
        settings = Settings.from_env()
        
        # Override defaults for webhook context
        # Use GCS for cursor/tracking storage in production, local for development
        storage_provider = os.environ.get('WEBHOOK_STORAGE_PROVIDER', 'gcs')
        job_runner = os.environ.get('WEBHOOK_JOB_RUNNER', 'cloudrun')
        
        settings.storage_provider = storage_provider
        settings.job_runner = job_runner
        
        print(f"🔧 Using storage provider: {storage_provider}")
        print(f"🔧 Using job runner: {job_runner}")
        
        # Create service factory
        _factory = ServiceFactory(settings)
        
        # Create required services
        try:
            # Storage for cursor and job tracking
            storage_service = _factory.create_storage_service()
            
            # Orchestration service for job management
            orchestration_service = _factory.create_orchestration_service()
            
            # Cursor manager for tracking Dropbox changes
            cursor_manager = CursorManager(
                storage_provider=storage_service.provider,
                cursor_file_path=os.environ.get('CURSOR_FILE_PATH', 'webhook/cursors.json')
            )
            
            # Job tracker for preventing duplicate processing
            job_tracker = JobTracker(
                storage_provider=storage_service.provider,
                tracking_file_path=os.environ.get('TRACKING_FILE_PATH', 'webhook/processed_jobs.json')
            )
            
            # Main webhook service
            _webhook_service = WebhookService(
                orchestration_service=orchestration_service,
                cursor_manager=cursor_manager,
                job_tracker=job_tracker,
                supported_formats=[
                    '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
                    '.aac', '.oga', '.ogg', '.flac', '.mov', '.avi', '.mkv',
                    '.wmv', '.flv', '.3gp'
                ]
            )
            
            print("✅ Webhook service initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing webhook service: {str(e)}")
            raise
    
    return _webhook_service


@functions_framework.http
def webhook_handler(request: Request):
    """
    Modern HTTP Cloud Function to handle webhook notifications
    Uses new modular architecture for better maintainability and testing
    
    Args:
        request: HTTP request from webhook notifications
    """
    try:
        # Handle webhook verification (GET request with challenge parameter)
        if request.method == 'GET':
            challenge = request.args.get('challenge')
            if challenge:
                print(f"✅ Webhook verification - returning challenge: {challenge}")
                return challenge, 200
            else:
                print("⚠️ GET request without challenge parameter")
                return 'Bad Request', 400
        
        # Handle actual webhook notifications (POST requests)
        if request.method != 'POST':
            return 'Method not allowed', 405
        
        # Get webhook service
        webhook_service = get_webhook_service()
        
        # Security: Verify signature for Dropbox webhooks
        if not _verify_dropbox_signature(request):
            return 'Unauthorized', 401
        
        # Parse webhook payload
        try:
            webhook_data = request.get_json(force=True)
            if not webhook_data:
                print("⚠️ Empty webhook payload")
                return 'Bad Request', 400
                
        except Exception as e:
            print(f"⚠️ Error parsing webhook JSON: {str(e)}")
            return 'Bad Request', 400
        
        print(f"📧 Received webhook notification")
        print(f"🔍 Payload keys: {list(webhook_data.keys())}")
        
        # Process the webhook notification asynchronously
        result = asyncio.run(webhook_service.process_notification(
            notification_data=webhook_data,
            handler_type="dropbox"
        ))
        
        if result["success"]:
            print(f"✅ Webhook processed successfully: {result['message']}")
            print(f"📊 Files processed: {result['files_processed']}, Jobs triggered: {result['jobs_triggered']}")
            return 'OK', 200
        else:
            print(f"❌ Webhook processing failed: {result.get('error', 'Unknown error')}")
            return 'Error', 500
        
    except Exception as e:
        print(f"❌ Unexpected error in webhook handler: {str(e)}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        return 'Error', 500


def _verify_dropbox_signature(request: Request) -> bool:
    """
    Verify Dropbox webhook signature
    
    Args:
        request: HTTP request
        
    Returns:
        True if signature is valid
    """
    try:
        # Get signature from headers
        dropbox_signature = request.headers.get('X-Dropbox-Signature')
        if not dropbox_signature:
            print("⚠️ Missing Dropbox signature - rejecting request")
            return False
        
        # Get request body
        request_body = request.get_data()
        
        # Use Dropbox handler for signature verification
        from services.webhook.handlers.dropbox import DropboxWebhookHandler
        
        # Create a temporary handler just for signature verification
        # (we don't need the full dependencies for this)
        handler = DropboxWebhookHandler(
            cursor_manager=None, 
            job_tracker=None
        )
        
        return handler.verify_webhook_signature(dropbox_signature, request_body)
        
    except Exception as e:
        print(f"❌ Error verifying signature: {str(e)}")
        return False


@functions_framework.http 
def webhook_status(request: Request):
    """
    Status endpoint for webhook service
    GET /status returns webhook service information
    """
    try:
        if request.method != 'GET':
            return 'Method not allowed', 405
        
        webhook_service = get_webhook_service()
        
        # Get service statistics
        stats = asyncio.run(webhook_service.get_processing_stats())
        
        # Get factory information
        factory_info = _factory.get_available_providers() if _factory else {}
        validation = _factory.validate_configuration() if _factory else {"valid": False}
        
        status_info = {
            "service": "webhook",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "storage_provider": os.environ.get('WEBHOOK_STORAGE_PROVIDER', 'gcs'),
                "job_runner": os.environ.get('WEBHOOK_JOB_RUNNER', 'cloudrun'),
                "valid": validation.get("valid", False)
            },
            "statistics": stats,
            "available_providers": factory_info
        }
        
        return json.dumps(status_info, indent=2), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        error_info = {
            "service": "webhook",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_info, indent=2), 500, {'Content-Type': 'application/json'}


@functions_framework.http
def webhook_admin(request: Request):
    """
    Admin endpoint for webhook service management
    POST /admin with actions like reset, cleanup, etc.
    """
    try:
        if request.method != 'POST':
            return 'Method not allowed', 405
        
        # Parse admin request
        try:
            admin_data = request.get_json(force=True)
            action = admin_data.get('action')
            
            if not action:
                return json.dumps({"error": "Missing 'action' parameter"}), 400
                
        except Exception as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}), 400
        
        webhook_service = get_webhook_service()
        
        # Handle different admin actions
        if action == "reset":
            # Reset all processing state
            confirm = admin_data.get('confirm', False)
            result = asyncio.run(webhook_service.reset_processing_state(confirm=confirm))
            
        elif action == "stats":
            # Get detailed statistics
            result = asyncio.run(webhook_service.get_processing_stats())
            
        elif action == "validate":
            # Validate configuration
            result = _factory.validate_configuration() if _factory else {"error": "Factory not initialized"}
            
        else:
            result = {"error": f"Unknown action: {action}"}
        
        return json.dumps(result, indent=2), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        error_info = {
            "action": admin_data.get('action') if 'admin_data' in locals() else 'unknown',
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_info, indent=2), 500, {'Content-Type': 'application/json'}


if __name__ == "__main__":
    # For local testing with functions-framework
    print("🧪 Running webhook handler locally...")
    print("Available endpoints:")
    print("  POST / - Main webhook handler") 
    print("  GET /status - Service status")
    print("  POST /admin - Admin actions")
    pass