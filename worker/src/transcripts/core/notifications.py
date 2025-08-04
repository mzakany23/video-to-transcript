"""
SMS notification service for job completion alerts
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from twilio.rest import Client
from google.cloud import secretmanager

from ..config import Config


class NotificationService:
    """Handles SMS notifications via Twilio"""
    
    def __init__(self, project_id: str):
        """Initialize notification service with Twilio credentials from Secret Manager"""
        self.project_id = project_id
        self.enabled = Config.ENABLE_SMS_NOTIFICATIONS
        self.to_number = Config.NOTIFICATION_PHONE_NUMBER
        
        if not self.enabled:
            print("📴 SMS notifications disabled")
            return
            
        # Initialize Secret Manager client
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Get Twilio credentials from Secret Manager
        try:
            twilio_creds = self._get_twilio_credentials()
            self.account_sid = twilio_creds['account_sid']
            self.auth_token = twilio_creds['auth_token']
            self.from_number = twilio_creds['from_number']
            self.verify_service_sid = twilio_creds.get('verify_service_sid')
            
            # Initialize Twilio client
            self.client = Client(self.account_sid, self.auth_token)
            print("📱 SMS notifications enabled")
            
        except Exception as e:
            print(f"⚠️ Failed to initialize SMS notifications: {str(e)}")
            self.enabled = False
    
    def _get_twilio_credentials(self) -> Dict[str, str]:
        """Retrieve Twilio credentials from Google Secret Manager"""
        secret_name = f"projects/{self.project_id}/secrets/{Config.TWILIO_SECRET_NAME}/versions/latest"
        
        try:
            response = self.secret_client.access_secret_version(request={"name": secret_name})
            secret_data = response.payload.data.decode("UTF-8")
            
            # Parse JSON credentials
            creds = json.loads(secret_data)
            
            # Validate required fields
            required_fields = ['account_sid', 'auth_token', 'from_number']
            for field in required_fields:
                if field not in creds:
                    raise ValueError(f"Missing required field in Twilio credentials: {field}")
            
            return creds
            
        except Exception as e:
            raise Exception(f"Failed to retrieve Twilio credentials: {str(e)}")
    
    def send_job_completion(self, job_summary: Dict[str, Any]) -> bool:
        """
        Send SMS notification for job completion
        
        Args:
            job_summary: Dictionary containing job completion details
                - processed_count: Number of files processed successfully
                - total_count: Total number of files attempted
                - duration: Job duration in seconds
                - failed_files: List of failed file names (optional)
                
        Returns:
            bool: True if notification sent successfully
        """
        if not self.enabled:
            return False
            
        try:
            # Format message
            processed = job_summary.get('processed_count', 0)
            total = job_summary.get('total_count', 0)
            duration = job_summary.get('duration', 0)
            
            # Convert duration to human readable format
            if duration > 3600:
                duration_str = f"{duration/3600:.1f} hours"
            elif duration > 60:
                duration_str = f"{duration/60:.1f} minutes"
            else:
                duration_str = f"{duration:.0f} seconds"
            
            # Build message
            message_parts = [
                f"🎬 Transcription Job Complete",
                f"✅ Processed: {processed}/{total} files",
                f"⏱️ Duration: {duration_str}"
            ]
            
            # Add failed files if any
            failed_files = job_summary.get('failed_files', [])
            if failed_files:
                message_parts.append(f"❌ Failed: {', '.join(failed_files[:3])}")
                if len(failed_files) > 3:
                    message_parts.append(f"... and {len(failed_files) - 3} more")
            
            message = "\n".join(message_parts)
            
            # Send SMS
            sms = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )
            
            print(f"📤 SMS notification sent: {sms.sid}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send SMS notification: {str(e)}")
            return False
    
    def send_job_error(self, error_message: str) -> bool:
        """
        Send SMS notification for job errors
        
        Args:
            error_message: Error description
            
        Returns:
            bool: True if notification sent successfully
        """
        if not self.enabled:
            return False
            
        try:
            message = f"🚨 Transcription Job Error\n\n{error_message[:100]}"
            
            sms = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )
            
            print(f"📤 Error SMS notification sent: {sms.sid}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send error SMS notification: {str(e)}")
            return False