#!/usr/bin/env python3
"""
Setup Gmail credentials in Google Secret Manager for email notifications
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from google.cloud import secretmanager
from google.api_core import exceptions


def create_gmail_secret():
    """Create Gmail credentials secret in Google Secret Manager"""
    
    # Get project ID from environment
    project_id = os.environ.get("PROJECT_ID")
    if not project_id:
        print("❌ Error: PROJECT_ID environment variable not set")
        print("   Please run: export PROJECT_ID=your-project-id")
        return False
    
    secret_name = os.environ.get("GMAIL_SECRET_NAME", "gmail-credentials")
    
    print(f"🔧 Setting up Gmail credentials in project: {project_id}")
    print(f"📝 Secret name: {secret_name}")
    
    # Get Gmail credentials from user
    print("\n📧 Enter your Gmail credentials:")
    print("   Note: You must use an App Password, not your regular Gmail password")
    print("   To create an App Password:")
    print("   1. Go to https://myaccount.google.com/security")
    print("   2. Enable 2-Step Verification if not already enabled")
    print("   3. Go to App passwords")
    print("   4. Create a new app password for 'Mail'")
    print()
    
    email = input("Gmail address: ").strip()
    if not email:
        print("❌ Email address cannot be empty")
        return False
    
    app_password = input("App Password (16 characters, no spaces): ").strip()
    if not app_password:
        print("❌ App password cannot be empty")
        return False
    
    # Remove any spaces from app password
    app_password = app_password.replace(" ", "")
    
    # Optional SMTP settings (use defaults if not provided)
    smtp_server = input("SMTP server (press Enter for smtp.gmail.com): ").strip()
    if not smtp_server:
        smtp_server = "smtp.gmail.com"
    
    smtp_port = input("SMTP port (press Enter for 587): ").strip()
    if not smtp_port:
        smtp_port = "587"
    
    # Create credentials JSON
    credentials = {
        "email": email,
        "app_password": app_password,
        "smtp_server": smtp_server,
        "smtp_port": smtp_port
    }
    
    credentials_json = json.dumps(credentials, indent=2)
    
    # Initialize Secret Manager client
    client = secretmanager.SecretManagerServiceClient()
    
    # Create the parent for the secret
    parent = f"projects/{project_id}"
    
    try:
        # Check if secret already exists
        secret_path = f"{parent}/secrets/{secret_name}"
        try:
            client.get_secret(request={"name": secret_path})
            print(f"\n⚠️  Secret '{secret_name}' already exists")
            
            # Ask if user wants to update it
            update = input("Do you want to update it? (y/n): ").lower()
            if update != 'y':
                print("❌ Setup cancelled")
                return False
            
            # Add new version to existing secret
            version_parent = secret_path
            response = client.add_secret_version(
                request={
                    "parent": version_parent,
                    "payload": {"data": credentials_json.encode("UTF-8")}
                }
            )
            print(f"✅ Updated secret version: {response.name}")
            
        except exceptions.NotFound:
            # Create new secret
            print(f"\n📦 Creating new secret: {secret_name}")
            
            secret = client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {
                        "replication": {
                            "automatic": {}
                        }
                    }
                }
            )
            
            print(f"✅ Created secret: {secret.name}")
            
            # Add the secret version with the credentials
            response = client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": credentials_json.encode("UTF-8")}
                }
            )
            print(f"✅ Added secret version: {response.name}")
        
        print("\n🎉 Gmail credentials successfully stored in Secret Manager!")
        print("\n📋 Next steps:")
        print("1. Set environment variables for your Cloud Run job:")
        print(f"   - GMAIL_SECRET_NAME={secret_name}")
        print(f"   - NOTIFICATION_EMAIL=recipient@example.com")
        print("   - ENABLE_EMAIL_NOTIFICATIONS=true")
        print("\n2. Make sure your Cloud Run service account has the 'Secret Manager Secret Accessor' role")
        print("\n3. Test by triggering a transcription job")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating secret: {str(e)}")
        print("\n🔍 Troubleshooting:")
        print("1. Make sure you have the necessary permissions")
        print("2. Ensure Secret Manager API is enabled in your project")
        print("3. Check that you're authenticated: gcloud auth application-default login")
        return False


if __name__ == "__main__":
    print("🚀 Gmail Secret Setup for Transcription Pipeline")
    print("=" * 50)
    
    success = create_gmail_secret()
    
    if not success:
        sys.exit(1)