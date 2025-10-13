#!/usr/bin/env python3
"""
List all Zoom recordings to debug API access
"""

import os
import sys
import json
from datetime import datetime

# Add the downloader directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from main import ZoomClient


def main():
    print("\n" + "=" * 80)
    print("Zoom Recordings Explorer")
    print("=" * 80 + "\n")

    # Check for credentials
    required_vars = ['ZOOM_ACCOUNT_ID', 'ZOOM_CLIENT_ID', 'ZOOM_CLIENT_SECRET']
    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nPlease set them using:")
        print("  export ZOOM_ACCOUNT_ID='your-account-id'")
        print("  export ZOOM_CLIENT_ID='your-client-id'")
        print("  export ZOOM_CLIENT_SECRET='your-client-secret'")
        sys.exit(1)

    try:
        # Create client
        client = ZoomClient()
        print("✅ ZoomClient initialized\n")

        # Get access token
        token = client.get_access_token()
        print(f"   Token (first 20 chars): {token[:20]}...\n")

        # List all recordings
        print("-" * 80)
        print("Fetching all recordings...")
        print("-" * 80 + "\n")

        data = client.list_all_recordings(user_id="me", page_size=100)

        # Display summary
        meetings = data.get('meetings', [])
        print(f"\n📊 Summary:")
        print(f"   Total recordings: {len(meetings)}")
        print(f"   Page size: {data.get('page_size', 'N/A')}")
        print(f"   Total records: {data.get('total_records', 'N/A')}")

        if not meetings:
            print("\n⚠️  No recordings found!")
            print("   This could mean:")
            print("   - No recordings exist in your account")
            print("   - The OAuth app doesn't have access to recordings")
            print("   - The recordings have been deleted")
            return

        # Display each recording
        print(f"\n{'=' * 80}")
        print("Available Recordings:")
        print(f"{'=' * 80}\n")

        for i, meeting in enumerate(meetings, 1):
            uuid = meeting.get('uuid', 'N/A')
            topic = meeting.get('topic', 'Untitled')
            start_time = meeting.get('start_time', 'N/A')
            duration = meeting.get('duration', 0)
            recording_count = meeting.get('recording_count', 0)
            total_size = meeting.get('total_size', 0)
            recording_files = meeting.get('recording_files', [])

            print(f"{i}. {topic}")
            print(f"   UUID: {uuid}")
            print(f"   Start Time: {start_time}")
            print(f"   Duration: {duration} minutes")
            print(f"   Recording Count: {recording_count}")
            print(f"   Total Size: {total_size / (1024*1024):.2f} MB")

            # List files
            if recording_files:
                print(f"   Files:")
                for rf in recording_files:
                    file_type = rf.get('file_type', 'N/A')
                    recording_type = rf.get('recording_type', 'N/A')
                    file_size = rf.get('file_size', 0)
                    status = rf.get('status', 'N/A')
                    print(f"      - {file_type} ({recording_type}): {file_size / (1024*1024):.2f} MB [Status: {status}]")

            print()

        # Test fetching a specific recording
        if meetings:
            print(f"{'=' * 80}")
            print("Testing get_meeting_recordings() on first recording...")
            print(f"{'=' * 80}\n")

            test_uuid = meetings[0].get('uuid')
            test_topic = meetings[0].get('topic')

            print(f"Attempting to fetch: {test_topic}")
            print(f"UUID: {test_uuid}\n")

            try:
                recording_details = client.get_meeting_recordings(test_uuid)
                print("✅ Successfully fetched recording details!")

                files = recording_details.get('recording_files', [])
                print(f"   Files found: {len(files)}")

                for f in files:
                    print(f"      - {f.get('file_type')} ({f.get('recording_type')})")
                    print(f"        Download URL: {f.get('download_url', 'N/A')[:60]}...")

            except Exception as e:
                print(f"❌ Failed to fetch recording details: {e}")

        # Save to file for reference
        output_file = 'zoom_recordings_list.json'
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Full response saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ Exploration complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
