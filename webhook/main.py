"""
Webhook Handler
Receives webhook notifications and triggers transcription jobs
"""

import json
import os
import hmac
import hashlib
from typing import Dict, Any, List
from datetime import datetime

import functions_framework
from google.cloud import run_v2
from flask import Request
import dropbox

@functions_framework.http
def webhook_handler(request: Request):
    """
    HTTP Cloud Function to handle Dropbox webhook notifications
    SECURITY: Early validation and rejection to prevent billing spikes
    
    Args:
        request: HTTP request from Dropbox webhook notifications
    """
    # Handle Dropbox webhook verification (GET request with challenge parameter)
    if request.method == 'GET':
        challenge = request.args.get('challenge')
        if challenge:
            print(f"✅ Dropbox webhook verification - returning challenge: {challenge}")
            return challenge, 200
        else:
            print("⚠️ GET request without challenge parameter")
            return 'Bad Request', 400
    
    # Handle actual webhook notifications (POST requests)
    if request.method != 'POST':
        return 'Method not allowed', 405
    
    # SECURITY: Verify Dropbox signature (the RIGHT way)
    dropbox_signature = request.headers.get('X-Dropbox-Signature')
    if not dropbox_signature:
        print("⚠️ Missing Dropbox signature - rejecting request")
        return 'Unauthorized', 401
    
    # Verify the signature using Dropbox app secret
    app_secret = os.environ.get('DROPBOX_APP_SECRET')
    if not app_secret:
        print("❌ Missing DROPBOX_APP_SECRET environment variable")
        return 'Server Error', 500
    
    request_body = request.get_data()
    expected_signature = hmac.new(
        app_secret.encode('utf-8'),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(dropbox_signature, expected_signature):
        print("⚠️ Invalid Dropbox signature - rejecting request")
        return 'Unauthorized', 401
    
    try:
        # Parse Dropbox webhook payload
        webhook_data = request.get_json(force=True)
        
        if not webhook_data or 'list_folder' not in webhook_data:
            print("⚠️ Invalid Dropbox webhook payload")
            return 'Bad Request', 400
        
        accounts = webhook_data.get('list_folder', {}).get('accounts', [])
        if not accounts:
            print("ℹ️ No accounts in webhook - ignoring")
            return 'OK', 200
        
        print(f"📧 Dropbox notification: {len(accounts)} account(s) with changes")
        
        # Get changed files and trigger individual jobs
        try:
            processor = WebhookProcessor()
            results = processor.process_webhook_notification(webhook_data)
            
            successful_jobs = sum(1 for r in results if r.get('success'))
            total_jobs = len(results)
            
            print(f"✅ Triggered {successful_jobs}/{total_jobs} transcription jobs")
            return 'OK', 200
            
        except Exception as e:
            print(f"❌ Error queuing work: {str(e)}")
            return 'Error', 500
        
    except Exception as e:
        print(f"❌ Error in webhook handler: {str(e)}")
        return 'Error', 500


class WebhookProcessor:
    """Processes webhooks and triggers individual jobs per file"""
    
    def __init__(self):
        """Initialize with minimal resources for fast webhook processing"""
        self.project_id = os.environ.get('PROJECT_ID')
        self.region = os.environ.get('GCP_REGION', 'us-east1')
        self.job_name = os.environ.get('WORKER_JOB_NAME', 'transcription-worker')
        
        # Initialize clients
        self.run_client = run_v2.JobsClient()
        self.job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
        
        # Initialize Dropbox client to check files
        access_token = os.environ.get('DROPBOX_ACCESS_TOKEN', '').strip()
        if not access_token:
            raise ValueError("DROPBOX_ACCESS_TOKEN required")
        self.dbx = dropbox.Dropbox(access_token)
        
        # Raw folder path
        self.raw_folder = "/jos-transcripts/raw"
        
        # Supported audio/video formats
        self.supported_formats = {
            '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
            '.aac', '.oga', '.ogg', '.flac', '.mov', '.avi', '.mkv',
            '.wmv', '.flv', '.3gp'
        }
    
    def process_webhook_notification(self, webhook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process webhook notification and trigger individual jobs per changed file
        
        Args:
            webhook_data: Dropbox webhook payload
            
        Returns:
            List of job trigger results
        """
        try:
            # Get recently changed files in raw folder
            changed_files = self.get_changed_audio_files()
            
            if not changed_files:
                print("ℹ️ No audio/video files found in raw folder")
                return []
            
            print(f"🎵 Found {len(changed_files)} audio/video files to process")
            
            # Trigger one job per file
            results = []
            for file_info in changed_files:
                result = self.trigger_job_for_file(file_info)
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error processing webhook notification: {str(e)}")
            return [{'success': False, 'error': str(e)}]
    
    def get_changed_audio_files(self) -> List[Dict[str, Any]]:
        """Get audio/video files from raw folder that need processing"""
        try:
            # List files in raw folder
            result = self.dbx.files_list_folder(self.raw_folder)
            files = result.entries
            
            # Get additional pages if they exist
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                files.extend(result.entries)
            
            audio_files = []
            for file_entry in files:
                if not hasattr(file_entry, 'path_display'):
                    continue
                    
                file_name = file_entry.name
                file_extension = os.path.splitext(file_name)[1].lower()
                
                # Check if it's a supported format
                if file_extension in self.supported_formats:
                    file_info = {
                        'name': file_name,
                        'path': file_entry.path_display,
                        'size': getattr(file_entry, 'size', 0),
                        'modified': getattr(file_entry, 'client_modified', None)
                    }
                    audio_files.append(file_info)
            
            return audio_files
            
        except Exception as e:
            print(f"❌ Error getting changed files: {str(e)}")
            return []
    
    def trigger_job_for_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a Cloud Run Job for a specific file
        
        Args:
            file_info: Dictionary with file details (name, path, etc.)
            
        Returns:
            Dictionary with job trigger results
        """
        try:
            file_name = file_info['name']
            file_path = file_info['path']
            
            print(f"🚀 Triggering job for file: {file_name}")
            
            # Create execution request for Cloud Run Job with specific file
            request = run_v2.RunJobRequest(
                name=self.job_path,
                overrides=run_v2.RunJobRequest.Overrides(
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            env=[
                                run_v2.EnvVar(name="PROCESS_SINGLE_FILE", value="true"),
                                run_v2.EnvVar(name="TARGET_FILE_PATH", value=file_path),
                                run_v2.EnvVar(name="TARGET_FILE_NAME", value=file_name),
                            ]
                        )
                    ]
                )
            )
            
            # Execute the job
            operation = self.run_client.run_job(request=request)
            
            # Get operation name properly
            operation_name = getattr(operation, 'name', str(operation))
            print(f"✅ Job triggered for {file_name}: {operation_name}")
            
            return {
                'success': True,
                'operation_name': operation_name,
                'file_name': file_name,
                'file_path': file_path
            }
            
        except Exception as e:
            print(f"❌ Error triggering job for {file_info.get('name', 'unknown')}: {str(e)}")
            return {'success': False, 'error': str(e), 'file_name': file_info.get('name')}


if __name__ == "__main__":
    # For local testing with functions-framework
    pass