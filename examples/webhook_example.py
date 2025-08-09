#!/usr/bin/env python3
"""
Example of using the modernized webhook architecture
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from services import ServiceFactory, Settings
from services.webhook import WebhookService, CursorManager, JobTracker


async def main():
    """Demonstrate webhook service usage"""
    
    print("=== Webhook Service Architecture Example ===\n")
    
    # Create development configuration
    print("1. Setting up development configuration:")
    dev_settings = Settings(
        storage_provider="local",
        transcription_provider="openai", 
        job_runner="local",
        environment="development",
        log_level="INFO"
    )
    
    # Configure local storage paths
    dev_settings.storage_configs["local"].config["base_path"] = "./webhook_storage"
    dev_settings.job_runner_configs["local"].config["work_dir"] = "./webhook_jobs"
    
    print(f"   Storage: {dev_settings.storage_provider}")
    print(f"   Job Runner: {dev_settings.job_runner}")
    print(f"   Environment: {dev_settings.environment}")
    
    # Create service factory
    factory = ServiceFactory(dev_settings)
    
    # Create required services
    print("\n2. Creating services:")
    try:
        # Storage for cursors and job tracking
        storage_service = factory.create_storage_service()
        print("   ✓ Storage service created")
        
        # Orchestration for job management  
        orchestration_service = factory.create_orchestration_service()
        print("   ✓ Orchestration service created")
        
        # Cursor manager for tracking changes
        cursor_manager = CursorManager(
            storage_provider=storage_service.provider,
            cursor_file_path="webhook/cursors.json"
        )
        print("   ✓ Cursor manager created")
        
        # Job tracker for preventing duplicates
        job_tracker = JobTracker(
            storage_provider=storage_service.provider,
            tracking_file_path="webhook/processed_jobs.json"
        )
        print("   ✓ Job tracker created")
        
        # Main webhook service
        webhook_service = WebhookService(
            orchestration_service=orchestration_service,
            cursor_manager=cursor_manager,
            job_tracker=job_tracker,
            supported_formats=['.mp3', '.mp4', '.wav', '.m4a']
        )
        print("   ✓ Webhook service created")
        
    except Exception as e:
        print(f"   ✗ Error creating services: {e}")
        return
    
    # Demonstrate webhook service capabilities
    print("\n3. Service capabilities:")
    
    # Get processing statistics
    stats = await webhook_service.get_processing_stats()
    print(f"   Processed files: {stats.get('processed_files', 0)}")
    print(f"   Supported formats: {len(stats.get('supported_formats', []))}")
    print(f"   Runner type: {stats.get('orchestration', {}).get('runner_type', 'unknown')}")
    
    # Demonstrate cursor operations
    print("\n4. Cursor management:")
    
    # Set a test cursor
    await cursor_manager.set_cursor("/test/folder", "test_cursor_12345")
    print("   ✓ Set test cursor")
    
    # Retrieve the cursor
    cursor = await cursor_manager.get_cursor("/test/folder")
    print(f"   ✓ Retrieved cursor: {cursor}")
    
    # List all cursors
    cursors = await cursor_manager.list_cursors()
    print(f"   ✓ Total cursors: {len(cursors)}")
    
    # Get cursor info
    cursor_info = await cursor_manager.get_cursor_info()
    print(f"   Storage provider: {cursor_info.get('storage_provider', 'unknown')}")
    
    # Demonstrate job tracking
    print("\n5. Job tracking:")
    
    # Mark a test file as processed
    await job_tracker.mark_processed(
        file_id="test_audio.mp3",
        job_id="job_12345",
        file_info={
            "name": "test_audio.mp3",
            "path": "/test/test_audio.mp3",
            "size": 1024000
        }
    )
    print("   ✓ Marked test file as processed")
    
    # Check if file is processed
    is_processed = await job_tracker.is_processed("test_audio.mp3")
    print(f"   ✓ File processed status: {is_processed}")
    
    # Get job record
    job_record = await job_tracker.get_job_record("test_audio.mp3")
    print(f"   ✓ Job record exists: {job_record is not None}")
    
    # List processed files
    processed_files = await job_tracker.list_processed_files(limit=5)
    print(f"   ✓ Processed files: {len(processed_files)}")
    
    # Get tracking info
    tracking_info = await job_tracker.get_tracking_info()
    print(f"   Storage provider: {tracking_info.get('storage_provider', 'unknown')}")
    
    # Simulate webhook notification processing
    print("\n6. Webhook notification processing:")
    
    # Simulate a Dropbox webhook payload (simplified)
    mock_webhook_data = {
        "list_folder": {
            "accounts": ["account123"]
        },
        "delta": {
            "users": ["user123"]
        }
    }
    
    print("   Simulating webhook notification...")
    
    # Note: This would normally require a real Dropbox client
    # For demo purposes, we'll just show the structure
    try:
        # This would fail with real Dropbox API calls in demo mode
        # result = await webhook_service.process_notification(
        #     notification_data=mock_webhook_data,
        #     handler_type="dropbox"
        # )
        # print(f"   ✓ Notification processed: {result['success']}")
        
        print("   ℹ️ Dropbox API calls skipped in demo mode")
        print("   ℹ️ In production, this would:")
        print("      - Verify webhook signature")
        print("      - Check for file changes using cursors") 
        print("      - Filter for supported formats")
        print("      - Skip already processed files")
        print("      - Trigger transcription jobs")
        print("      - Update tracking records")
        
    except Exception as e:
        print(f"   ℹ️ Expected error in demo mode: {type(e).__name__}")
    
    # Clean up demo data
    print("\n7. Cleanup:")
    try:
        await cursor_manager.reset_all_cursors()
        await job_tracker.reset_tracking()
        print("   ✓ Demo data cleaned up")
    except Exception as e:
        print(f"   ⚠️ Cleanup warning: {e}")
    
    print("\n=== Webhook Service Demo Complete ===")
    
    print("\nKey improvements in the new architecture:")
    print("• Modular services with clean interfaces")
    print("• Pluggable storage providers (local, GCS, Dropbox)")
    print("• Pluggable job runners (Cloud Run, local)")
    print("• Separated cursor management from job tracking")  
    print("• Configuration-driven provider selection")
    print("• Async/await throughout for better performance")
    print("• Comprehensive error handling and logging")
    print("• Easy to test with dependency injection")
    print("• Cloud-agnostic design for portability")


if __name__ == "__main__":
    asyncio.run(main())