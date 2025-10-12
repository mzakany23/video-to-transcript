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
from google.cloud import run_v2, storage
from flask import Request
import dropbox

# Initialize Sentry for error tracking
try:
    import sentry_sdk
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.environ.get('SENTRY_ENVIRONMENT', 'production'),
            release=os.environ.get('VERSION', 'webhook@unknown'),
            send_default_pii=True,
            traces_sample_rate=0.1  # 10% of transactions for performance monitoring
        )
        print(f"✅ Sentry initialized - version: {os.environ.get('VERSION', 'unknown')}")
    else:
        print("ℹ️ Sentry DSN not configured, error tracking disabled")
except ImportError:
    print("⚠️ Sentry SDK not installed, error tracking disabled")
except Exception as e:
    print(f"⚠️ Failed to initialize Sentry: {e}")

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
        print(f"🔍 Full webhook payload: {json.dumps(webhook_data, indent=2)}")
        
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
        
        # Initialize Cloud Storage for cursor persistence
        self.storage_client = storage.Client()
        self.bucket_name = f"{self.project_id}-webhook-cursors"
        self.cursor_blob_name = "dropbox_cursors.json"
        
        # Job tracking bucket and file
        self.job_tracking_bucket_name = f"{self.project_id}-job-tracking"
        self.job_tracking_blob_name = "processed_jobs.json"
        
        # Initialize Dropbox client with refresh token capability
        refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN', '').strip()
        app_key = os.environ.get('DROPBOX_APP_KEY', '').strip()
        app_secret = os.environ.get('DROPBOX_APP_SECRET', '').strip()
        
        if refresh_token and app_key and app_secret:
            print("🔄 Initializing webhook Dropbox client with refresh token...")
            self.dbx = dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token
            )
        else:
            print("🔑 Falling back to access token for webhook...")
            access_token = os.environ.get('DROPBOX_ACCESS_TOKEN', '').strip()
            if not access_token:
                raise ValueError("DROPBOX_ACCESS_TOKEN or refresh token setup required")
            self.dbx = dropbox.Dropbox(access_token)
        
        # Raw folder path
        self.raw_folder = os.environ.get('DROPBOX_RAW_FOLDER', '/transcripts/raw')
        
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
            # Get only the files that actually changed using cursors
            changed_files = self.get_changed_files_with_cursor()
            
            if not changed_files:
                print("ℹ️ No new changes found in monitored folders")
                return []
            
            print(f"🎵 Found {len(changed_files)} changed audio/video files")
            
            # Load job tracking to filter out already processed files
            processed_jobs = self._load_job_tracking()
            
            # Filter out already processed files
            unprocessed_files = []
            for file_info in changed_files:
                file_id = file_info['path'].replace('/', '_').replace(' ', '_')
                if file_id not in processed_jobs:
                    unprocessed_files.append(file_info)
                    print(f"  ✅ Will process: {file_info['name']}")
                else:
                    print(f"  ⏭️ Already processed: {file_info['name']}")
            
            if not unprocessed_files:
                print("ℹ️ All changed files have already been processed")
                return []
            
            print(f"🚀 Triggering jobs for {len(unprocessed_files)} unprocessed files")
            
            # Trigger one job per unprocessed file
            results = []
            for file_info in unprocessed_files:
                result = self.trigger_job_for_file(file_info)
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error processing webhook notification: {str(e)}")
            return [{'success': False, 'error': str(e)}]
    
    def _load_cursors(self) -> Dict[str, str]:
        """Load cursors from Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(self.cursor_blob_name)
            
            if blob.exists():
                cursor_data = blob.download_as_text()
                cursors = json.loads(cursor_data)
                print(f"📥 Loaded cursors from storage: {list(cursors.keys())}")
                return cursors
            else:
                print("📝 No existing cursors found, starting fresh")
                return {}
                
        except Exception as e:
            print(f"⚠️ Error loading cursors: {str(e)}, starting fresh")
            return {}
    
    def _save_cursors(self, cursors: Dict[str, str]):
        """Save cursors to Cloud Storage"""
        try:
            print(f"🔧 Attempting to save cursors to bucket: {self.bucket_name}")
            print(f"🔧 Project ID: {self.project_id}, Region: {self.region}")
            
            # Ensure bucket exists
            bucket = self.storage_client.bucket(self.bucket_name)
            try:
                print(f"🔧 Checking if bucket exists...")
                bucket.reload()
                print(f"✅ Bucket exists: {self.bucket_name}")
            except Exception as reload_error:
                # Create bucket if it doesn't exist
                print(f"❌ Bucket reload failed: {str(reload_error)}")
                print(f"📦 Creating cursor storage bucket: {self.bucket_name}")
                try:
                    bucket = self.storage_client.create_bucket(self.bucket_name, location=self.region)
                    print(f"✅ Successfully created bucket: {self.bucket_name}")
                except Exception as create_error:
                    print(f"❌ Bucket creation failed: {str(create_error)}")
                    raise
            
            # Save cursors
            print(f"💾 Uploading cursor data...")
            blob = bucket.blob(self.cursor_blob_name)
            cursor_data = json.dumps(cursors, indent=2)
            blob.upload_from_string(cursor_data, content_type='application/json')
            print(f"✅ Saved cursors to storage: {list(cursors.keys())}")
            
        except Exception as e:
            print(f"❌ Error saving cursors: {str(e)}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
    
    def _load_job_tracking(self) -> Dict[str, Any]:
        """Load job tracking data from Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.job_tracking_bucket_name)
            blob = bucket.blob(self.job_tracking_blob_name)
            
            if blob.exists():
                job_data = blob.download_as_text()
                processed_jobs = json.loads(job_data)
                print(f"📥 Loaded job tracking from Cloud Storage: {len(processed_jobs)} processed files")
                return processed_jobs
            else:
                print("📝 No existing job tracking found")
                return {}
                
        except Exception as e:
            print(f"⚠️ Error loading job tracking: {str(e)}, assuming no processed files")
            return {}
    
    def get_changed_files_with_cursor(self) -> List[Dict[str, Any]]:
        """Get only files that actually changed using Dropbox cursor API"""
        try:
            # Load existing cursors from storage
            cursors = self._load_cursors()
            cursor = cursors.get(self.raw_folder)
            
            if cursor is None:
                # First time - get initial cursor
                print("🔄 Getting initial cursor for raw folder")
                result = self.dbx.files_list_folder(self.raw_folder)
                cursor = result.cursor
                cursors[self.raw_folder] = cursor
                self._save_cursors(cursors)
                
                # On first run, don't process existing files (avoid initial flood)
                print("ℹ️ Initial cursor set - skipping existing files to prevent flood")
                return []
            
            # Get changes since last cursor
            print(f"🔄 Checking for changes since last cursor")
            try:
                result = self.dbx.files_list_folder_continue(cursor)
            except dropbox.exceptions.ApiError as e:
                if 'reset' in str(e).lower():
                    print("⚠️ Cursor expired, getting fresh cursor")
                    result = self.dbx.files_list_folder(self.raw_folder)
                    cursors[self.raw_folder] = result.cursor
                    self._save_cursors(cursors)
                    return []  # Skip processing on reset
                else:
                    raise
            
            # Update cursor for next time
            cursors[self.raw_folder] = result.cursor
            self._save_cursors(cursors)
            
            # Process only the changes
            changed_files = []
            for entry in result.entries:
                print(f"🔍 Change detected: {getattr(entry, 'name', 'NO_NAME')} (type: {type(entry).__name__})")
                
                # Skip deleted files
                if isinstance(entry, dropbox.files.DeletedMetadata):
                    print(f"  ⏭️ Skipping deleted file")
                    continue
                
                # Only process files in our raw folder
                if not hasattr(entry, 'path_display') or not entry.path_display.startswith(self.raw_folder):
                    print(f"  ⏭️ Skipping file outside raw folder")
                    continue
                
                file_name = entry.name
                file_extension = os.path.splitext(file_name)[1].lower()
                
                # Check if it's a supported audio/video format
                if file_extension in self.supported_formats:
                    print(f"  ✅ New audio/video file: {file_name}")
                    file_info = {
                        'name': file_name,
                        'path': entry.path_display,
                        'size': getattr(entry, 'size', 0),
                        'modified': getattr(entry, 'client_modified', None)
                    }
                    changed_files.append(file_info)
                else:
                    print(f"  ⏭️ Skipping unsupported format: {file_extension}")
            
            return changed_files
            
        except Exception as e:
            print(f"❌ Error getting changed files with cursor: {str(e)}")
            # Fallback to full scan on error
            return self._fallback_get_audio_files()
    
    def _fallback_get_audio_files(self) -> List[Dict[str, Any]]:
        """Fallback method - scan all files (use only on error)"""
        try:
            print("⚠️ Using fallback method - scanning all files")
            result = self.dbx.files_list_folder(self.raw_folder)
            files = result.entries
            
            audio_files = []
            for file_entry in files:
                if not hasattr(file_entry, 'path_display'):
                    continue
                    
                file_name = file_entry.name
                file_extension = os.path.splitext(file_name)[1].lower()
                
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
            print(f"❌ Error in fallback method: {str(e)}")
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
            file_size = file_info.get('size', 0)
            file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0

            print(f"🚀 Triggering job for file: {file_name} ({file_size_mb:.1f}MB)")

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
                                run_v2.EnvVar(name="TARGET_FILE_SIZE_MB", value=f"{file_size_mb:.1f}"),
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