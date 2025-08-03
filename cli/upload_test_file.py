#!/usr/bin/env python3
"""Upload test file to Dropbox for processing"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'worker', 'src'))

from transcripts.core.dropbox_handler import DropboxHandler

def main():
    # Connect to Dropbox
    dbx = DropboxHandler()
    print('📤 Uploading test file to Dropbox...')

    # Path to test file
    test_file_path = "../data/raw/1.mp4"
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return
    
    file_size = os.path.getsize(test_file_path) / (1024 * 1024)
    print(f"📁 Found test file: 1.mp4 ({file_size:.1f} MB)")
    
    try:
        # Upload file to raw folder
        with open(test_file_path, 'rb') as f:
            import dropbox
            dbx.dbx.files_upload(
                f.read(),
                '/raw/1.mp4',
                mode=dropbox.files.WriteMode.overwrite
            )
        
        print(f"✅ Uploaded 1.mp4 to Dropbox /raw/ folder")
        
        # Verify upload
        result = dbx.dbx.files_list_folder('/raw')
        files = result.entries
        print(f"📂 Raw folder now contains {len(files)} files:")
        for file_entry in files:
            if hasattr(file_entry, 'path_display'):
                size_mb = getattr(file_entry, 'size', 0) / (1024 * 1024)
                print(f"  - {file_entry.name} ({size_mb:.1f} MB)")
                
    except Exception as e:
        print(f"❌ Error uploading file: {e}")

if __name__ == "__main__":
    main()