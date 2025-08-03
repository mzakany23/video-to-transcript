"""
Webhook Handler
Receives webhook notifications and triggers transcription jobs
"""

import json
import os
import hmac
import hashlib
from typing import Dict, Any
from datetime import datetime

import functions_framework
from google.cloud import run_v2
from flask import Request

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
        
        # SECURITY: Lightweight processing - trigger Cloud Run Job for heavy work
        try:
            processor = WebhookProcessor()
            result = processor.trigger_transcription_job(webhook_data)
            
            if result.get('success'):
                print(f"✅ Triggered transcription job")
            else:
                print(f"❌ Failed to trigger job: {result.get('error')}")
            
            return 'OK', 200
            
        except Exception as e:
            print(f"❌ Error queuing work: {str(e)}")
            return 'Error', 500
        
    except Exception as e:
        print(f"❌ Error in webhook handler: {str(e)}")
        return 'Error', 500


class WebhookProcessor:
    """Lightweight webhook processor - triggers Cloud Run Jobs for heavy processing"""
    
    def __init__(self):
        """Initialize with minimal resources for fast webhook processing"""
        self.project_id = os.environ.get('PROJECT_ID')
        self.region = os.environ.get('GCP_REGION', 'us-east1')
        self.job_name = os.environ.get('WORKER_JOB_NAME', 'transcription-worker')
        
        # Initialize Cloud Run client for job triggering
        self.run_client = run_v2.JobsClient()
        self.job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
    
    def trigger_transcription_job(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        SECURITY: Lightweight operation - trigger Cloud Run Job for heavy processing
        Don't do expensive operations here to prevent billing spikes
        
        Args:
            webhook_data: Dropbox webhook payload
            
        Returns:
            Dictionary with processing results
        """
        try:
            print(f"🚀 Triggering Cloud Run Job: {self.job_name}")
            
            # Create execution request for Cloud Run Job
            request = run_v2.RunJobRequest(
                name=self.job_path,
                overrides=run_v2.RunJobRequest.Overrides(
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            env=[
                                run_v2.EnvVar(name="WEBHOOK_TRIGGER", value="true"),
                                run_v2.EnvVar(name="DROPBOX_WEBHOOK_DATA", value=json.dumps(webhook_data)),
                            ]
                        )
                    ]
                )
            )
            
            # Execute the job
            operation = self.run_client.run_job(request=request)
            
            print(f"✅ Cloud Run Job triggered: {operation.name}")
            
            return {
                'success': True,
                'operation_name': operation.name,
                'job_name': self.job_name
            }
            
        except Exception as e:
            print(f"❌ Error triggering Cloud Run Job: {str(e)}")
            return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    # For local testing with functions-framework
    pass