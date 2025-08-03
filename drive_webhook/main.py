"""
Google Drive Webhook Handler
Receives push notifications from Google Drive and publishes messages to Pub/Sub
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

import functions_framework
from google.cloud import pubsub_v1
from google.cloud import run_v2
from flask import Request


@functions_framework.http
def drive_webhook_handler(request: Request):
    """
    HTTP Cloud Function to handle Google Drive push notifications
    SECURITY: Early validation and rejection to prevent billing spikes
    
    Args:
        request: HTTP request from Google Drive push notifications
    """
    # SECURITY: Immediate basic validation (cheapest operations first)
    if request.method != 'POST':
        return 'Method not allowed', 405
        
    # SECURITY: Quick header validation before any expensive operations
    required_headers = ['X-Goog-Channel-Id', 'X-Goog-Resource-Id', 'X-Goog-Resource-State']
    for header in required_headers:
        if header not in request.headers:
            print(f"⚠️ Missing header: {header} - rejecting request")
            return 'Bad Request', 400
    
    try:
        # Get the notification data
        channel_id = request.headers.get('X-Goog-Channel-Id')
        resource_id = request.headers.get('X-Goog-Resource-Id')
        resource_state = request.headers.get('X-Goog-Resource-State')
        
        # SECURITY: Validate channel ID format (basic sanity check)
        if not channel_id or not channel_id.startswith('transcription-'):
            print(f"⚠️ Invalid channel ID: {channel_id} - rejecting request")
            return 'Unauthorized', 401
        
        print(f"📧 Drive notification: channel={channel_id}, resource={resource_id}, state={resource_state}")
        
        # Only process 'update' and 'sync' events (ignore others quickly)
        if resource_state not in ['update', 'sync']:
            print(f"Ignoring resource state: {resource_state}")
            return 'OK', 200
        
        # SECURITY: Lightweight processing - trigger Cloud Run Job for heavy work
        try:
            processor = DriveWebhookProcessor()
            result = processor.trigger_transcription_job(channel_id, resource_id, resource_state)
            
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


class DriveWebhookProcessor:
    """Lightweight webhook processor - triggers Cloud Run Jobs for heavy processing"""
    
    def __init__(self):
        """Initialize with minimal resources for fast webhook processing"""
        self.project_id = os.environ.get('PROJECT_ID')
        self.region = os.environ.get('CLOUD_RUN_REGION', 'us-east1')
        self.job_name = os.environ.get('CLOUD_RUN_JOB_NAME', 'transcription-processor-job')
        
        # Initialize Cloud Run client for job triggering
        self.run_client = run_v2.JobsClient()
        self.job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
    
    def trigger_transcription_job(self, channel_id: str, resource_id: str, resource_state: str) -> Dict[str, Any]:
        """
        SECURITY: Lightweight operation - trigger Cloud Run Job for heavy processing
        Don't do expensive operations here to prevent billing spikes
        
        Args:
            channel_id: Google Drive channel ID
            resource_id: Google Drive resource ID  
            resource_state: State of the resource (update, sync, etc.)
            
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
                                run_v2.EnvVar(name="CHANNEL_ID", value=channel_id),
                                run_v2.EnvVar(name="RESOURCE_ID", value=resource_id),
                                run_v2.EnvVar(name="RESOURCE_STATE", value=resource_state),
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
    # For local testing
    pass