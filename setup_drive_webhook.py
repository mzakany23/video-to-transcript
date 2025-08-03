#!/usr/bin/env python3
"""
Script to set up Google Drive push notifications for the transcription pipeline
"""

import json
import uuid
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    """Set up Google Drive push notifications"""
    
    # Configuration - UPDATE THESE VALUES FOR YOUR DEPLOYMENT
    WEBHOOK_URL = "https://us-east1-YOUR-PROJECT.cloudfunctions.net/drive-webhook-handler"
    FOLDER_ID = "YOUR-GOOGLE-DRIVE-FOLDER-ID"  # Raw folder to monitor
    
    # Load service account credentials
    service_account_file = Path("service-account.json")
    if not service_account_file.exists():
        print("❌ service-account.json not found. Make sure you've run terraform apply first.")
        return
    
    try:
        # Authenticate with Google Drive
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(
            str(service_account_file), scopes=scopes
        )
        service = build('drive', 'v3', credentials=creds)
        
        print(f"🔧 Setting up Google Drive webhook...")
        print(f"📁 Monitoring folder: {FOLDER_ID}")
        print(f"🔗 Webhook URL: {WEBHOOK_URL}")
        
        # Generate a unique channel ID
        channel_id = f"transcription-{uuid.uuid4().hex[:8]}"
        
        # Create the watch request
        watch_request = {
            'id': channel_id,
            'type': 'web_hook',
            'address': WEBHOOK_URL,
            'payload': True  # Include resource data in notifications
        }
        
        # Set up the push notification
        result = service.files().watch(
            fileId=FOLDER_ID,
            body=watch_request
        ).execute()
        
        print(f"✅ Successfully set up Google Drive webhook!")
        print(f"   Channel ID: {result.get('id')}")
        print(f"   Resource ID: {result.get('resourceId')}")
        print(f"   Expiration: {result.get('expiration')}")
        
        # Save the channel info for later reference
        channel_info = {
            'channel_id': result.get('id'),
            'resource_id': result.get('resourceId'),
            'webhook_url': WEBHOOK_URL,
            'folder_id': FOLDER_ID,
            'expiration': result.get('expiration')
        }
        
        with open('drive_webhook_info.json', 'w') as f:
            json.dump(channel_info, f, indent=2)
        
        print(f"💾 Channel info saved to drive_webhook_info.json")
        
        print(f"\n🎉 Setup complete! Your transcription pipeline is now active.")
        print(f"📤 Upload audio/video files to: https://drive.google.com/drive/folders/{FOLDER_ID}")
        print(f"🔄 Files will be automatically transcribed and results saved to the processed folder.")
        
    except Exception as e:
        print(f"❌ Error setting up webhook: {str(e)}")
        print("\nPossible issues:")
        print("1. Service account doesn't have access to the folder")
        print("2. Google Drive API is not enabled")
        print("3. Webhook URL is not accessible")

if __name__ == "__main__":
    main()