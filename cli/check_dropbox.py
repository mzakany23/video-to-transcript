#!/usr/bin/env python3
"""Quick script to check Dropbox folder contents"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'worker', 'src'))

from transcripts.core.dropbox_handler import DropboxHandler

def main():
    # Connect to Dropbox
    dbx = DropboxHandler()
    print('📁 Checking Dropbox folders...')

    # List files in raw folder
    try:
        result = dbx.dbx.files_list_folder('/raw')
        files = result.entries
        print(f'\n📂 Raw folder contains {len(files)} files:')
        for file_entry in files:
            if hasattr(file_entry, 'path_display'):
                size_mb = getattr(file_entry, 'size', 0) / (1024 * 1024)
                print(f'  - {file_entry.name} ({size_mb:.1f} MB)')
    except Exception as e:
        print(f'❌ Error listing raw folder: {e}')

    # List files in processed folder  
    try:
        result = dbx.dbx.files_list_folder('/processed')
        files = result.entries
        print(f'\n📁 Processed folder contains {len(files)} files:')
        for file_entry in files:
            if hasattr(file_entry, 'path_display'):
                size_mb = getattr(file_entry, 'size', 0) / (1024 * 1024)
                print(f'  - {file_entry.name} ({size_mb:.1f} MB)')
    except Exception as e:
        print(f'❌ Error listing processed folder: {e}')

if __name__ == "__main__":
    main()