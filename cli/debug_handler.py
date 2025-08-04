#!/usr/bin/env python3
"""Debug DropboxHandler initialization"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'worker', 'src'))

from transcripts.core.dropbox_handler import DropboxHandler
from transcripts.config import Config
import dropbox

def debug_handler():
    print(f"🔍 Token from config: {Config.DROPBOX_ACCESS_TOKEN[:50]}...")
    print(f"🔍 Token length: {len(Config.DROPBOX_ACCESS_TOKEN)}")
    
    # Test direct Dropbox call first
    try:
        print("🧪 Testing direct Dropbox connection...")
        dbx = dropbox.Dropbox(Config.DROPBOX_ACCESS_TOKEN)
        account = dbx.users_get_current_account()
        print(f"✅ Direct connection works: {account.name.display_name}")
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        return
    
    # Now test our DropboxHandler
    try:
        print("🧪 Testing DropboxHandler...")
        handler = DropboxHandler()
        print("✅ DropboxHandler works!")
    except Exception as e:
        print(f"❌ DropboxHandler failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_handler()