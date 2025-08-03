#!/usr/bin/env python3
"""
Script to find Google Drive folder IDs for the transcription system
"""

import json
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    """Find the folder IDs for raw and processed folders"""
    
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
        
        print("🔍 Searching for folders...")
        
        # Search for folders by name
        folder_names = ['raw', 'processed', 'transcripts']
        
        for folder_name in folder_names:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields='files(id,name,parents)').execute()
            folders = results.get('files', [])
            
            print(f"\n📁 Folders named '{folder_name}':")
            if not folders:
                print(f"   No folders found with name '{folder_name}'")
            else:
                for folder in folders:
                    folder_id = folder['id']
                    folder_name_result = folder['name']
                    parents = folder.get('parents', [])
                    
                    print(f"   📁 {folder_name_result}")
                    print(f"      ID: {folder_id}")
                    print(f"      Parents: {parents}")
                    print(f"      URL: https://drive.google.com/drive/folders/{folder_id}")
        
        # Also search for any folders shared with the service account
        print(f"\n🔍 All folders accessible to service account:")
        query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query, 
            fields='files(id,name,parents)',
            pageSize=20
        ).execute()
        folders = results.get('files', [])
        
        for folder in folders:
            folder_id = folder['id']
            folder_name = folder['name']
            parents = folder.get('parents', [])
            
            print(f"   📁 {folder_name}")
            print(f"      ID: {folder_id}")
            print(f"      URL: https://drive.google.com/drive/folders/{folder_id}")
        
        print(f"\n💡 Instructions:")
        print(f"1. Find your 'raw' folder ID from the list above")
        print(f"2. Copy the folder ID")
        print(f"3. Add it to terraform/terraform.tfvars:")
        print(f"   monitored_folder_id = \"your-folder-id-here\"")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Make sure your service account has access to the Google Drive folders.")

if __name__ == "__main__":
    main()