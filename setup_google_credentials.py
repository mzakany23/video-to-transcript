#!/usr/bin/env python3
"""
Setup script for Google Drive API credentials
Guides user through the credential setup process
"""

import os
import json
from pathlib import Path


def check_credentials():
    """Check if Google API credentials are properly set up"""
    credentials_file = Path('credentials.json')
    token_file = Path('token.json')

    print("🔍 Checking Google API credentials setup...")

    if not credentials_file.exists():
        print("\n❌ Missing: credentials.json")
        print("📋 To set up Google Drive API credentials:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable the Google Drive API")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
        print("5. Choose 'Desktop application'")
        print("6. Download the JSON file and save as 'credentials.json' in this directory")
        print("\n📁 Expected file location:", credentials_file.absolute())
        return False

    # Validate credentials file format
    try:
        with open(credentials_file) as f:
            creds_data = json.load(f)

        if 'installed' not in creds_data:
            print("❌ Invalid credentials.json format")
            print("Make sure you downloaded 'OAuth client ID' credentials, not service account")
            return False

        print("✅ credentials.json found and valid")

    except json.JSONDecodeError:
        print("❌ credentials.json is not valid JSON")
        return False

    if token_file.exists():
        print("✅ token.json found (OAuth token already generated)")
    else:
        print("⚠️  token.json not found (will be created on first run)")

    return True


def setup_environment():
    """Set up required environment variables and files"""
    env_file = Path('.env')

    print("\n🔧 Setting up environment...")

    # Check for OpenAI API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not found in environment")

        if not env_file.exists():
            print("Creating .env file...")
            with open(env_file, 'w') as f:
                f.write("# OpenAI API Configuration\n")
                f.write("OPENAI_API_KEY=your_openai_api_key_here\n")
                f.write("\n# Google Drive Configuration (optional)\n")
                f.write("GOOGLE_DRIVE_FOLDER_NAME=Transcription Pipeline\n")

        print(f"📝 Please add your OpenAI API key to {env_file}")
    else:
        print("✅ OPENAI_API_KEY found in environment")

    return True


def test_google_drive_connection():
    """Test Google Drive connection"""
    print("\n🧪 Testing Google Drive connection...")

    try:
        from google_drive_handler import GoogleDriveHandler

        drive = GoogleDriveHandler()
        folder_info = drive.setup_folder_structure()

        print("✅ Google Drive connection successful!")
        print("📁 Folder structure:")
        print(f"   Main: {folder_info['main_folder_url']}")
        print(f"   Raw: {folder_info['raw_folder_url']}")
        print(f"   Processed: {folder_info['processed_folder_url']}")

        return True

    except Exception as e:
        print(f"❌ Google Drive connection failed: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Google Drive API Setup for Transcription Pipeline\n")

    # Check credentials
    if not check_credentials():
        print("\n⏸️  Setup incomplete. Please download credentials.json first.")
        return False

    # Setup environment
    setup_environment()

    # Test connection
    if test_google_drive_connection():
        print("\n🎉 Setup complete! You can now run the transcription pipeline.")
        print("\n📋 Next steps:")
        print("1. Share the Google Drive folders with your team")
        print("2. Test by uploading a video/audio file to the 'raw' folder")
        print("3. Run: uv run python transcribe_drive.py")
        return True
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        return False


if __name__ == '__main__':
    main()