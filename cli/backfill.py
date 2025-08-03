"""
Backfill transcription CLI - processes existing files in Dropbox
"""

import argparse
from datetime import datetime

# Import from worker service (need to add path)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'worker', 'src'))

from transcripts.core.dropbox_handler import DropboxHandler
from transcripts.core.transcription import TranscriptionService
from transcripts.core.audio_processor import AudioProcessor
from transcripts.config import Config


class BackfillProcessor:
    """Processes existing files in Dropbox raw folder for backfill transcription"""
    
    def __init__(self):
        """Initialize with core services"""
        self.dropbox_handler = DropboxHandler()
        self.transcription_service = TranscriptionService()
        self.audio_processor = AudioProcessor()
        
        print(f"🔧 Backfill processor initialized")
        folder_info = self.dropbox_handler.get_folder_info()
        print(f"📁 Raw folder: {folder_info['raw_folder']}")
        print(f"📁 Processed folder: {folder_info['processed_folder']}")
    
    def process_all_files(self, max_files: int = None, dry_run: bool = False):
        """Process all audio/video files in the raw folder"""
        print(f"🚀 Starting backfill transcription job...")
        
        # Get all audio/video files
        files_to_process = self.dropbox_handler.get_audio_video_files()
        
        if not files_to_process:
            print("ℹ️ No audio/video files found to process")
            return
        
        if max_files:
            files_to_process = files_to_process[:max_files]
            print(f"📊 Processing {len(files_to_process)} files (limited to {max_files})")
        else:
            print(f"📊 Processing {len(files_to_process)} files")
        
        if dry_run:
            print(f"\n📋 Files that would be processed:")
            for i, file_info in enumerate(files_to_process, 1):
                size_mb = file_info.get('size', 0) / (1024 * 1024)
                print(f"   {i}. {file_info.get('name')} ({size_mb:.1f}MB)")
            return
        
        successful = 0
        failed = 0
        
        for i, file_info in enumerate(files_to_process, 1):
            file_name = file_info.get('name')
            file_path = file_info.get('path')
            
            print(f"\n🔄 [{i}/{len(files_to_process)}] Processing: {file_name}")
            
            try:
                # Download file
                temp_file = self.dropbox_handler.download_file(file_path, file_name)
                if not temp_file:
                    failed += 1
                    continue
                
                # Process audio
                processed_file = self.audio_processor.prepare_audio_file(temp_file, file_name)
                
                # Transcribe
                result = self.transcription_service.transcribe_audio(processed_file)
                
                if result.get('success'):
                    # Upload results
                    upload_result = self.dropbox_handler.upload_transcript_results(
                        result['transcript_data'], 
                        file_name
                    )
                    
                    if 'error' not in upload_result:
                        successful += 1
                        print(f"✅ [{i}/{len(files_to_process)}] Completed: {file_name}")
                    else:
                        failed += 1
                        print(f"❌ [{i}/{len(files_to_process)}] Upload failed: {file_name}")
                else:
                    failed += 1
                    print(f"❌ [{i}/{len(files_to_process)}] Transcription failed: {file_name}")
                
                # Clean up temporary files
                if temp_file and temp_file.exists():
                    temp_file.unlink()
                if processed_file != temp_file and processed_file.exists():
                    processed_file.unlink()
                    
            except Exception as e:
                failed += 1
                print(f"❌ [{i}/{len(files_to_process)}] Error processing {file_name}: {str(e)}")
        
        print(f"\n📊 Backfill job completed:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        folder_info = self.dropbox_handler.get_folder_info()
        print(f"   📁 Results in: {folder_info['processed_folder']}")


def main():
    """Main entry point for backfill CLI"""
    parser = argparse.ArgumentParser(description='Backfill transcription of Dropbox files')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    parser.add_argument('--dry-run', action='store_true', help='List files without processing')
    
    args = parser.parse_args()
    
    try:
        # Validate configuration
        Config.validate()
        
        processor = BackfillProcessor()
        
        processor.process_all_files(
            max_files=args.max_files,
            dry_run=args.dry_run
        )
            
    except KeyboardInterrupt:
        print("\n⚠️ Job interrupted by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()