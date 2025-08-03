#!/usr/bin/env python3
"""
Google Drive API handler for transcription system
Handles authentication, file monitoring, and uploads/downloads
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io


class GoogleDriveHandler:
    """Handles Google Drive API operations for the transcription pipeline using service account authentication"""

    # Scopes required for Drive access
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata'
    ]

    # Supported file formats for transcription
    SUPPORTED_FORMATS = {
        '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
        '.aac', '.oga', '.ogg', '.flac', '.mov', '.avi'
    }

    def __init__(self, service_account_file: str = 'service-account.json'):
        """Initialize Google Drive handler with service account authentication"""
        self.service_account_file = service_account_file
        self.service = None
        self.raw_folder_id = None
        self.processed_folder_id = None

        # Authenticate and build service
        self._authenticate()

    def _authenticate(self):
        """Handle Google Drive API authentication using service account only"""
        if not os.path.exists(self.service_account_file):
            raise FileNotFoundError(
                f"Service account file not found: {self.service_account_file}. "
                "Please ensure the service account key file exists."
            )

        try:
            print("🔑 Using Service Account authentication...")
            creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.SCOPES
            )
            print(f"✅ Service Account authenticated: {creds.service_account_email}")

            # Build the Drive service
            self.service = build('drive', 'v3', credentials=creds)
            print("✅ Google Drive API authenticated successfully")

        except Exception as e:
            raise Exception(f"Service Account authentication failed: {e}")

    def setup_folder_structure(self, shared_folder_name: str = "Transcription Pipeline") -> Dict[str, str]:
        """
        Create or find the shared folder structure:
        Transcription Pipeline/
        ├── raw/
        └── processed/
        """
        try:
            # Check if main folder exists
            main_folder = self._find_folder_by_name(shared_folder_name)
            if not main_folder:
                main_folder = self._create_folder(shared_folder_name)
                print(f"Created main folder: {shared_folder_name}")

            main_folder_id = main_folder['id']

            # Check for raw and processed subfolders
            raw_folder = self._find_folder_by_name("raw", parent_id=main_folder_id)
            if not raw_folder:
                raw_folder = self._create_folder("raw", parent_id=main_folder_id)
                print("Created 'raw' subfolder")

            processed_folder = self._find_folder_by_name("processed", parent_id=main_folder_id)
            if not processed_folder:
                processed_folder = self._create_folder("processed", parent_id=main_folder_id)
                print("Created 'processed' subfolder")

            self.raw_folder_id = raw_folder['id']
            self.processed_folder_id = processed_folder['id']

            folder_info = {
                'main_folder_id': main_folder_id,
                'raw_folder_id': self.raw_folder_id,
                'processed_folder_id': self.processed_folder_id,
                'main_folder_url': f"https://drive.google.com/drive/folders/{main_folder_id}",
                'raw_folder_url': f"https://drive.google.com/drive/folders/{self.raw_folder_id}",
                'processed_folder_url': f"https://drive.google.com/drive/folders/{self.processed_folder_id}",
            }

            print(f"\n📁 Folder structure ready:")
            print(f"Main folder: {folder_info['main_folder_url']}")
            print(f"Raw files: {folder_info['raw_folder_url']}")
            print(f"Processed files: {folder_info['processed_folder_url']}")

            return folder_info

        except Exception as e:
            print(f"Error setting up folder structure: {e}")
            raise

    def _find_folder_by_name(self, name: str, parent_id: Optional[str] = None) -> Optional[Dict]:
        """Find a folder by name, optionally within a parent folder"""
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = self.service.files().list(q=query).execute()
        folders = results.get('files', [])
        return folders[0] if folders else None

    def _create_folder(self, name: str, parent_id: Optional[str] = None) -> Dict:
        """Create a new folder in Google Drive"""
        folder_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_id:
            folder_metadata['parents'] = [parent_id]

        folder = self.service.files().create(body=folder_metadata, fields='id,name').execute()
        return folder

    def get_new_files_in_raw(self, processed_jobs: List[str] = None) -> List[Dict]:
        """Get list of new audio/video files in raw folder that haven't been processed"""
        if not self.raw_folder_id:
            raise ValueError("Raw folder ID not set. Run setup_folder_structure() first.")

        processed_jobs = processed_jobs or []

        # Query for files in raw folder
        query = (
            f"'{self.raw_folder_id}' in parents and "
            f"trashed=false and "
            f"mimeType != 'application/vnd.google-apps.folder'"
        )

        results = self.service.files().list(
            q=query,
            fields="files(id,name,size,modifiedTime,mimeType)"
        ).execute()

        files = results.get('files', [])
        new_files = []

        for file in files:
            # Check if file is supported format
            file_name = file['name']
            file_extension = Path(file_name).suffix.lower()

            if file_extension in self.SUPPORTED_FORMATS:
                # Check if already processed
                if file['id'] not in processed_jobs:
                    new_files.append(file)

        return new_files

    def download_file(self, file_id: str, destination_path: Path) -> bool:
        """Download a file from Google Drive to local path"""
        try:
            request = self.service.files().get_media(fileId=file_id)

            # Create destination directory if needed
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            # Download file
            with open(destination_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"Download progress: {int(status.progress() * 100)}%")

            print(f"✅ Downloaded: {destination_path}")
            return True

        except Exception as e:
            print(f"❌ Error downloading file {file_id}: {e}")
            return False

    def upload_transcript_results(self, transcript_data: Dict, source_file_name: str) -> Dict[str, str]:
        """Upload transcript results (JSON and TXT) to processed folder"""
        if not self.processed_folder_id:
            raise ValueError("Processed folder ID not set. Run setup_folder_structure() first.")

        base_name = Path(source_file_name).stem
        results = {}

        try:
            # Upload JSON file
            json_content = json.dumps(transcript_data, indent=2, ensure_ascii=False)
            json_file_id = self._upload_text_content(
                content=json_content,
                filename=f"{base_name}.json",
                mime_type="application/json"
            )
            results['json_file_id'] = json_file_id

            # Upload TXT file
            txt_content = transcript_data.get('text', '')
            if transcript_data.get('compressed'):
                txt_content += '\n\n[Note: Audio was compressed to meet API size limits]'

            txt_file_id = self._upload_text_content(
                content=txt_content,
                filename=f"{base_name}.txt",
                mime_type="text/plain"
            )
            results['txt_file_id'] = txt_file_id

            print(f"✅ Uploaded transcript results for: {source_file_name}")
            return results

        except Exception as e:
            print(f"❌ Error uploading transcript results: {e}")
            raise

    def _upload_text_content(self, content: str, filename: str, mime_type: str) -> str:
        """Upload text content as a file to the processed folder"""
        # Create temporary file
        temp_file = Path(f"conversation/{filename}")
        temp_file.parent.mkdir(exist_ok=True)

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)

        try:
            # Upload to Drive
            file_metadata = {
                'name': filename,
                'parents': [self.processed_folder_id]
            }

            media = MediaFileUpload(str(temp_file), mimetype=mime_type)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            return file.get('id')

        finally:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()

    def get_folder_info(self) -> Dict[str, str]:
        """Get current folder configuration"""
        return {
            'raw_folder_id': self.raw_folder_id,
            'processed_folder_id': self.processed_folder_id,
            'raw_folder_url': f"https://drive.google.com/drive/folders/{self.raw_folder_id}" if self.raw_folder_id else None,
            'processed_folder_url': f"https://drive.google.com/drive/folders/{self.processed_folder_id}" if self.processed_folder_id else None,
        }


def main():
    """Test the Google Drive handler"""
    try:
        drive = GoogleDriveHandler()
        folder_info = drive.setup_folder_structure()

        print("\n🔍 Checking for new files...")
        new_files = drive.get_new_files_in_raw()

        if new_files:
            print(f"Found {len(new_files)} new file(s):")
            for file in new_files:
                print(f"  - {file['name']} ({file.get('size', 'unknown')} bytes)")
        else:
            print("No new files found in raw folder")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    main()